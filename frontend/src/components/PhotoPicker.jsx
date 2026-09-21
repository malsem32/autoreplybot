import { useRef, useState } from "react";
import { api } from "../api/client.js";
import Button from "./ui/Button.jsx";

/**
 * Uploads an image via /api/uploads/photo and reports back its server-side
 * `path` (what the backend stores on AutoresponderRule/BroadcastCampaign).
 * `previewUrl` is what to show right away (existing photo's `/api/uploads/*`
 * URL when editing, or a local object URL right after picking a new file).
 */
export default function PhotoPicker({ previewUrl, onChange }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const { path, url } = await api.uploadPhoto(file);
      onChange({ path, previewUrl: url });
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  function handleRemove() {
    onChange(null);
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleFile}
      />

      {previewUrl ? (
        <div className="relative inline-block">
          <img
            src={previewUrl}
            alt="Прикреплённое фото"
            className="h-32 w-32 rounded-xl object-cover border border-slate-700"
          />
          <button
            type="button"
            onClick={handleRemove}
            className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-red-600 text-white text-xs flex items-center justify-center"
            aria-label="Удалить фото"
          >
            ✕
          </button>
        </div>
      ) : (
        <Button
          type="button"
          variant="secondary"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? "Загрузка…" : "+ Прикрепить фото"}
        </Button>
      )}

      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
    </div>
  );
}
