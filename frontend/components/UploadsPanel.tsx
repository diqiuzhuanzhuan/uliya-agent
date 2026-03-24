"use client";

import { ChangeEvent } from "react";

import { UploadItem } from "@/types/agent";

type UploadsPanelProps = {
  busy: boolean;
  items: UploadItem[];
  onUpload: (file: File) => void;
};

export function UploadsPanel({ busy, items, onUpload }: UploadsPanelProps) {
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onUpload(file);
      event.target.value = "";
    }
  };

  return (
    <div className="config-group">
      <span className="config-label">上传资料</span>
      <label className="upload-box">
        <input disabled={busy} onChange={handleFileChange} type="file" />
        <span>{busy ? "处理中..." : "上传文本文件，为后续 RAG/检索做准备。"}</span>
      </label>

      <div className="upload-list">
        {items.length === 0 ? (
          <p className="trace-content">暂无上传资料。</p>
        ) : (
          items.map((item) => (
            <article className="upload-item" key={item.id}>
              <strong>{item.filename}</strong>
              <p>{item.preview || "空文件或非文本内容。"}</p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
