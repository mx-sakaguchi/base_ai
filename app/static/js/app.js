/**
 * PDF Tools フロントエンド
 *
 * - 結合タブ: 複数 PDF アップロード（同時ドロップ対応）→ サムネイル付きページ並べ替え → 結合
 * - 分解タブ: 1 PDF アップロード → ルール指定 → ZIP ダウンロード（フォルダ構成付き）
 * - プリセット管理
 *
 * 依存ライブラリ:
 *   - SortableJS: ドラッグ&ドロップ並べ替え
 *   - PDF.js (pdfjs-dist): ページサムネイル描画（CDN 読み込み失敗時は代替表示）
 */

"use strict";

// =====================================================
// PDF.js ワーカー設定
// =====================================================
if (typeof pdfjsLib !== "undefined") {
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/legacy/build/pdf.worker.min.js";
}

// =====================================================
// 共通ユーティリティ
// =====================================================

/**
 * ステータスメッセージを表示する
 * @param {HTMLElement} el
 * @param {string} msg
 * @param {'success'|'error'|'loading'} type
 */
function showStatus(el, msg, type = "success") {
  el.textContent = msg;
  el.className = `status-msg ${type}`;
  el.classList.remove("hidden");
}

function hideStatus(el) {
  el.classList.add("hidden");
}

/**
 * バイナリ Blob をダウンロードさせる
 * @param {Blob} blob
 * @param {string} filename
 */
function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * API エラーメッセージを取り出す
 */
async function extractErrorMessage(response) {
  try {
    const json = await response.json();
    return json.detail || JSON.stringify(json);
  } catch {
    return `HTTP ${response.status}`;
  }
}

/**
 * XSS 対策用 HTML エスケープ
 */
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * ファイルが PDF かどうか判定する（MIME type または拡張子で確認）
 * @param {File} file
 * @returns {boolean}
 */
function isPdfFile(file) {
  return (
    file.type === "application/pdf" ||
    file.type === "application/x-pdf" ||
    file.name.toLowerCase().endsWith(".pdf")
  );
}

// =====================================================
// タブ切替
// =====================================================
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.tab;
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((s) => {
      s.classList.remove("active");
      s.classList.add("hidden");
    });
    btn.classList.add("active");
    const section = document.getElementById(`tab-${target}`);
    section.classList.remove("hidden");
    section.classList.add("active");
  });
});

// =====================================================
// PDF.js サムネイル生成
// =====================================================

/** サムネイル幅 (px) - A4 比率で高さを算出 */
const THUMB_WIDTH = 80;

/**
 * File オブジェクトから各ページのサムネイル (dataURL) を生成して返す。
 * PDF.js が利用不可の場合は null の配列を返す（代替表示に fallback）。
 *
 * @param {File} file
 * @param {number} pageCount
 * @param {function(number, number): void} [onProgress] - (current, total) コールバック
 * @returns {Promise<Array<string|null>>}
 */
async function generateThumbnails(file, pageCount, onProgress) {
  if (typeof pdfjsLib === "undefined") {
    // PDF.js が読み込まれていない場合はプレースホルダ
    return new Array(pageCount).fill(null);
  }

  const thumbnails = [];
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

    for (let pageNum = 1; pageNum <= pageCount; pageNum++) {
      // 進捗コールバック（5ページごと or 最終ページ）
      if (onProgress && (pageNum % 5 === 0 || pageNum === pageCount)) {
        onProgress(pageNum, pageCount);
        // ブラウザに制御を戻してUIを更新させる
        await new Promise((r) => setTimeout(r, 0));
      }

      const page = await pdf.getPage(pageNum);
      const viewport = page.getViewport({ scale: 1.0 });
      const scale = THUMB_WIDTH / viewport.width;
      const scaledViewport = page.getViewport({ scale });

      const canvas = document.createElement("canvas");
      canvas.width = Math.ceil(scaledViewport.width);
      canvas.height = Math.ceil(scaledViewport.height);

      await page.render({
        canvasContext: canvas.getContext("2d"),
        viewport: scaledViewport,
      }).promise;

      thumbnails.push(canvas.toDataURL("image/jpeg", 0.75));
      // ページのリソースを解放
      page.cleanup();
    }
  } catch (err) {
    console.warn("サムネイル生成エラー:", err);
    // エラー時は生成済み分 + 残りを null で埋める
    while (thumbnails.length < pageCount) thumbnails.push(null);
  }

  return thumbnails;
}

// =====================================================
// 結合タブ
// =====================================================

/**
 * アップロード済みファイル情報
 * @type {Array<{file_id: string, original_filename: string, page_count: number}>}
 */
const mergeFiles = [];

/**
 * 結合用ページリスト
 * @type {Array<{file_id: string, page_number: number, label: string, thumbnail: string|null}>}
 */
const mergePages = [];

const mergeDropZone = document.getElementById("merge-drop-zone");
const mergeFileInput = document.getElementById("merge-file-input");
const mergeFileList = document.getElementById("merge-file-list");
const mergeFilesUl = document.getElementById("merge-files");
const mergePageArea = document.getElementById("merge-page-area");
const mergeSortable = document.getElementById("merge-sortable");
const mergeExecuteBtn = document.getElementById("merge-execute-btn");
const mergeStatus = document.getElementById("merge-status");

// ドラッグ&ドロップ
mergeDropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  mergeDropZone.classList.add("dragover");
});
mergeDropZone.addEventListener("dragleave", () => mergeDropZone.classList.remove("dragover"));
mergeDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  mergeDropZone.classList.remove("dragover");
  handleMergeFiles(e.dataTransfer.files);
});
mergeFileInput.addEventListener("change", () => {
  handleMergeFiles(mergeFileInput.files);
  // 同じファイルを再選択できるようリセット
  mergeFileInput.value = "";
});

/**
 * 複数ファイルを処理する。
 * - PDF 以外のファイルは除外してエラーメッセージを表示する
 * - 同名ファイルは UUID ベースの file_id で内部的に区別される
 *
 * @param {FileList|File[]} fileList
 */
async function handleMergeFiles(fileList) {
  const files = Array.from(fileList);
  const skipped = [];

  for (const file of files) {
    if (!isPdfFile(file)) {
      skipped.push(file.name);
      continue;
    }
    await uploadMergeFile(file);
  }

  if (skipped.length > 0) {
    showStatus(
      mergeStatus,
      `PDF ではないファイルをスキップしました: ${skipped.map(escHtml).join(", ")}`,
      "error"
    );
  }
}

/**
 * 1ファイルをアップロードし、サムネイルを生成してページリストに追加する
 * @param {File} file
 */
async function uploadMergeFile(file) {
  showStatus(mergeStatus, `"${escHtml(file.name)}" をアップロード中...`, "loading");

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/merge/upload", { method: "POST", body: formData });
  if (!res.ok) {
    const msg = await extractErrorMessage(res);
    showStatus(mergeStatus, `"${escHtml(file.name)}" アップロード失敗: ${msg}`, "error");
    return;
  }

  const info = await res.json();
  mergeFiles.push(info);
  renderMergeFileList();

  // サムネイル生成（ローカルファイルから PDF.js で描画）
  showStatus(
    mergeStatus,
    `"${escHtml(file.name)}" のサムネイルを生成中... (0/${info.page_count})`,
    "loading"
  );

  const thumbs = await generateThumbnails(file, info.page_count, (cur, total) => {
    showStatus(
      mergeStatus,
      `"${escHtml(file.name)}" のサムネイルを生成中... (${cur}/${total})`,
      "loading"
    );
  });

  // ページリストに追加
  for (let p = 1; p <= info.page_count; p++) {
    mergePages.push({
      file_id: info.file_id,
      page_number: p,
      label: info.original_filename,
      thumbnail: thumbs[p - 1] || null,
    });
  }

  renderMergePageList();
  hideStatus(mergeStatus);
}

/**
 * アップロード済みファイル一覧を描画する
 */
function renderMergeFileList() {
  mergeFilesUl.innerHTML = "";
  mergeFiles.forEach((f) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="file-badge">${escHtml(f.original_filename)}</span>
      <span class="file-page-count">${f.page_count} ページ</span>
      <small style="color:#999">ID: ${f.file_id.slice(0, 8)}...</small>
    `;
    mergeFilesUl.appendChild(li);
  });
  mergeFileList.classList.remove("hidden");
}

/**
 * ページカード一覧を描画する（サムネイル表示）
 */
function renderMergePageList() {
  mergeSortable.innerHTML = "";

  mergePages.forEach((pg, idx) => {
    const div = document.createElement("div");
    div.className = "page-item";
    div.dataset.idx = idx;

    // サムネイル: 取得済みなら <img>、未取得ならプレースホルダ
    const thumbEl = pg.thumbnail
      ? `<img class="page-thumb" src="${pg.thumbnail}" alt="p.${pg.page_number}" loading="lazy" />`
      : `<div class="page-thumb-placeholder">p.${pg.page_number}</div>`;

    div.innerHTML = `
      <span class="drag-handle">⠿</span>
      ${thumbEl}
      <div class="page-card-info">
        <span class="page-card-filename" title="${escHtml(pg.label)}">${escHtml(pg.label)}</span>
        <span class="page-card-num">p.${pg.page_number}</span>
      </div>
      <button class="remove-page" data-idx="${idx}" title="このページを除外">✕</button>
    `;

    mergeSortable.appendChild(div);
  });

  mergePageArea.classList.remove("hidden");

  // 削除ボタンイベント
  mergeSortable.querySelectorAll(".remove-page").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const i = parseInt(e.currentTarget.dataset.idx, 10);
      mergePages.splice(i, 1);
      renderMergePageList();
    });
  });
}

// SortableJS でページ並べ替え（ドラッグ&ドロップ）
Sortable.create(mergeSortable, {
  animation: 150,
  handle: ".drag-handle",
  ghostClass: "sortable-ghost",
  chosenClass: "sortable-chosen",
  onEnd: (evt) => {
    if (evt.oldIndex === evt.newIndex) return;
    const [moved] = mergePages.splice(evt.oldIndex, 1);
    mergePages.splice(evt.newIndex, 0, moved);
    // DOM 側は SortableJS が更新済みなので data-idx を再同期する必要がある
    // renderMergePageList は呼ばず、data-idx のみ更新
    mergeSortable.querySelectorAll(".page-item").forEach((el, i) => {
      el.dataset.idx = i;
      el.querySelector(".remove-page").dataset.idx = i;
    });
  },
});

// 結合実行
mergeExecuteBtn.addEventListener("click", async () => {
  if (mergePages.length === 0) {
    showStatus(mergeStatus, "ページが1つも指定されていません", "error");
    return;
  }
  const outputName = document.getElementById("merge-output-name").value.trim() || "merged.pdf";
  const payload = {
    pages: mergePages.map((p) => ({ file_id: p.file_id, page_number: p.page_number })),
    output_filename: outputName,
  };

  showStatus(mergeStatus, "結合処理中...", "loading");
  mergeExecuteBtn.disabled = true;

  try {
    const res = await fetch("/api/merge/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await extractErrorMessage(res);
      showStatus(mergeStatus, `結合失敗: ${msg}`, "error");
      return;
    }
    const blob = await res.blob();
    downloadBlob(blob, outputName.endsWith(".pdf") ? outputName : outputName + ".pdf");
    showStatus(mergeStatus, "結合完了！ダウンロードが始まります。", "success");
  } catch (err) {
    showStatus(mergeStatus, `エラー: ${err.message}`, "error");
  } finally {
    mergeExecuteBtn.disabled = false;
  }
});

// =====================================================
// 分解タブ
// =====================================================

/** アップロード中の分解対象ファイル ID */
let splitFileId = null;
/** アップロード中の分解対象ファイルの元ファイル名 */
let splitOriginalFilename = "";

const splitDropZone = document.getElementById("split-drop-zone");
const splitFileInput = document.getElementById("split-file-input");
const splitFileInfo = document.getElementById("split-file-info");
const splitFileName = document.getElementById("split-file-name");
const splitPageCount = document.getElementById("split-page-count");
const splitRuleArea = document.getElementById("split-rule-area");
const splitStatus = document.getElementById("split-status");
const splitExecuteBtn = document.getElementById("split-execute-btn");
const fixedPagesGroup = document.getElementById("fixed-pages-group");
const customRangesGroup = document.getElementById("custom-ranges-group");
const presetManager = document.getElementById("preset-manager");
const splitPresetSelect = document.getElementById("split-preset-select");

// ドラッグ&ドロップ
splitDropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  splitDropZone.classList.add("dragover");
});
splitDropZone.addEventListener("dragleave", () => splitDropZone.classList.remove("dragover"));
splitDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  splitDropZone.classList.remove("dragover");
  if (e.dataTransfer.files[0]) uploadSplitFile(e.dataTransfer.files[0]);
});
splitFileInput.addEventListener("change", () => {
  if (splitFileInput.files[0]) uploadSplitFile(splitFileInput.files[0]);
});

async function uploadSplitFile(file) {
  showStatus(splitStatus, `"${escHtml(file.name)}" をアップロード中...`, "loading");
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/split/upload", { method: "POST", body: formData });
  if (!res.ok) {
    const msg = await extractErrorMessage(res);
    showStatus(splitStatus, `アップロード失敗: ${msg}`, "error");
    return;
  }

  const info = await res.json();
  splitFileId = info.file_id;
  splitOriginalFilename = info.original_filename;

  splitFileName.textContent = info.original_filename;
  splitPageCount.textContent = `${info.page_count} ページ`;
  splitFileInfo.classList.remove("hidden");
  splitRuleArea.classList.remove("hidden");
  presetManager.classList.remove("hidden");
  hideStatus(splitStatus);
  loadPresets();
}

// 分解方法の切替
document.querySelectorAll('input[name="split-rule-type"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const val = radio.value;
    fixedPagesGroup.classList.toggle("hidden", val !== "fixed_pages");
    customRangesGroup.classList.toggle("hidden", val !== "custom_ranges");
  });
});

// 分解実行
splitExecuteBtn.addEventListener("click", async () => {
  if (!splitFileId) {
    showStatus(splitStatus, "PDF がアップロードされていません", "error");
    return;
  }
  const ruleType = document.querySelector('input[name="split-rule-type"]:checked').value;
  const tplInput = document.getElementById("split-filename-tpl").value.trim();
  const payload = {
    file_id: splitFileId,
    split_rule_type: ruleType,
    // 空欄の場合はデフォルトテンプレートを使用
    filename_template: tplInput || "{original_name}_{index:03d}.pdf",
    fixed_pages_count:
      ruleType === "fixed_pages"
        ? parseInt(document.getElementById("split-fixed-count").value, 10)
        : null,
    custom_ranges:
      ruleType === "custom_ranges"
        ? document.getElementById("split-custom-ranges").value.trim()
        : null,
    // 元ファイル名を渡して ZIP 内フォルダ名・{original_name} 展開に使用
    original_filename: splitOriginalFilename,
  };

  showStatus(splitStatus, "分解処理中...", "loading");
  splitExecuteBtn.disabled = true;

  try {
    const res = await fetch("/api/split/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await extractErrorMessage(res);
      showStatus(splitStatus, `分解失敗: ${msg}`, "error");
      return;
    }
    const blob = await res.blob();
    // ZIP ファイル名は元ファイル名ベースにする
    const zipName = splitOriginalFilename
      ? splitOriginalFilename.replace(/\.pdf$/i, "") + ".zip"
      : "split_result.zip";
    downloadBlob(blob, zipName);
    showStatus(splitStatus, "分解完了！ZIP ダウンロードが始まります。", "success");
  } catch (err) {
    showStatus(splitStatus, `エラー: ${err.message}`, "error");
  } finally {
    splitExecuteBtn.disabled = false;
  }
});

// =====================================================
// プリセット管理
// =====================================================

let presets = [];

async function loadPresets() {
  const res = await fetch("/api/presets/");
  if (!res.ok) return;
  presets = await res.json();
  renderPresetSelect();
  renderPresetList();
}

function renderPresetSelect() {
  splitPresetSelect.innerHTML = '<option value="">-- 選択してください --</option>';
  presets.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.preset_name;
    splitPresetSelect.appendChild(opt);
  });
}

function renderPresetList() {
  const ul = document.getElementById("preset-list");
  ul.innerHTML = "";
  if (presets.length === 0) {
    ul.innerHTML = '<li style="color:#999;font-size:0.9rem;">登録済みプリセットなし</li>';
    return;
  }
  presets.forEach((p) => {
    const li = document.createElement("li");
    li.className = "preset-item";
    const desc =
      p.split_rule_type === "fixed_pages"
        ? `${p.fixed_pages_count} ページごと`
        : `範囲: ${p.custom_ranges}`;
    li.innerHTML = `
      <span class="preset-item-name">${escHtml(p.preset_name)}</span>
      <span class="preset-item-desc">${desc} / ${escHtml(p.filename_template)}</span>
      <button class="btn btn-danger" data-id="${p.id}">削除</button>
    `;
    li.querySelector("button").addEventListener("click", () => deletePreset(p.id));
    ul.appendChild(li);
  });
}

// プリセット読み込み
document.getElementById("split-load-preset-btn").addEventListener("click", () => {
  const id = parseInt(splitPresetSelect.value, 10);
  if (!id) return;
  const p = presets.find((x) => x.id === id);
  if (!p) return;

  document.querySelector(`input[name="split-rule-type"][value="${p.split_rule_type}"]`).checked =
    true;
  fixedPagesGroup.classList.toggle("hidden", p.split_rule_type !== "fixed_pages");
  customRangesGroup.classList.toggle("hidden", p.split_rule_type !== "custom_ranges");

  if (p.split_rule_type === "fixed_pages") {
    document.getElementById("split-fixed-count").value = p.fixed_pages_count || 1;
  } else {
    document.getElementById("split-custom-ranges").value = p.custom_ranges || "";
  }
  document.getElementById("split-filename-tpl").value = p.filename_template;
});

// プリセット保存モーダル
const presetModal = document.getElementById("preset-modal");
document.getElementById("split-save-preset-btn").addEventListener("click", () => {
  presetModal.classList.remove("hidden");
  document.getElementById("preset-name-input").focus();
});
document.getElementById("preset-modal-close-btn").addEventListener("click", () => {
  presetModal.classList.add("hidden");
});

document.getElementById("preset-save-confirm-btn").addEventListener("click", async () => {
  const name = document.getElementById("preset-name-input").value.trim();
  if (!name) {
    alert("プリセット名を入力してください");
    return;
  }

  const ruleType = document.querySelector('input[name="split-rule-type"]:checked').value;
  const tplInput = document.getElementById("split-filename-tpl").value.trim();
  const payload = {
    preset_name: name,
    mode: "split",
    split_rule_type: ruleType,
    fixed_pages_count:
      ruleType === "fixed_pages"
        ? parseInt(document.getElementById("split-fixed-count").value, 10)
        : null,
    custom_ranges:
      ruleType === "custom_ranges"
        ? document.getElementById("split-custom-ranges").value.trim()
        : null,
    filename_template: tplInput || "{original_name}_{index:03d}.pdf",
  };

  const res = await fetch("/api/presets/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const msg = await extractErrorMessage(res);
    alert(`保存失敗: ${msg}`);
    return;
  }
  presetModal.classList.add("hidden");
  document.getElementById("preset-name-input").value = "";
  await loadPresets();
});

async function deletePreset(id) {
  if (!confirm("このプリセットを削除しますか？")) return;
  const res = await fetch(`/api/presets/${id}`, { method: "DELETE" });
  if (!res.ok) {
    alert("削除に失敗しました");
    return;
  }
  await loadPresets();
}

// =====================================================
// 初期化
// =====================================================
loadPresets();
