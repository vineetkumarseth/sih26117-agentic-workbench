import React, { useEffect, useRef, useState } from "react";
import { Camera, X, RotateCcw, Check } from "lucide-react";

export default function CameraCapture({ open, onClose, onCapture }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const [shot, setShot] = useState(null); // dataUrl once captured
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setShot(null);
    setError(null);

    let cancelled = false;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch(() => {
        setError("Couldn't access the camera. Check your browser's camera permission for this site.");
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [open]);

  function handleCapture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    setShot(canvas.toDataURL("image/jpeg", 0.88));
  }

  function handleUsePhoto() {
    if (!shot) return;
    const base64 = shot.split(",")[1];
    onCapture({ base64, preview: shot });
    handleClose();
  }

  function handleClose() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    onClose();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70" onClick={handleClose}>
      <div
        className="flex w-[min(560px,92vw)] flex-col overflow-hidden rounded-md border border-graphite-600 bg-graphite-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-graphite-600 px-4 py-3">
          <div className="flex items-center gap-2">
            <Camera size={15} className="text-amber-500" strokeWidth={1.75} />
            <p className="text-sm text-ink-100">Take a photo for the vision agent</p>
          </div>
          <button onClick={handleClose} className="rounded-sm p-1 text-ink-500 hover:bg-graphite-700 hover:text-ink-100">
            <X size={16} />
          </button>
        </div>

        <div className="relative aspect-video bg-black">
          {error ? (
            <div className="flex h-full items-center justify-center px-6 text-center text-xs text-alert-400">
              {error}
            </div>
          ) : shot ? (
            <img src={shot} alt="Captured frame" className="h-full w-full object-contain" />
          ) : (
            <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-contain" />
          )}
          <canvas ref={canvasRef} className="hidden" />
        </div>

        <div className="flex items-center justify-center gap-3 border-t border-graphite-600 px-4 py-3">
          {error ? (
            <button
              onClick={handleClose}
              className="rounded-sm bg-graphite-700 px-4 py-2 text-xs text-ink-300 hover:bg-graphite-600"
            >
              Close
            </button>
          ) : !shot ? (
            <button
              onClick={handleCapture}
              className="flex items-center gap-2 rounded-full bg-amber-500 px-5 py-2.5 text-xs font-medium text-graphite-950 hover:bg-amber-400"
            >
              <Camera size={14} strokeWidth={2} />
              Capture
            </button>
          ) : (
            <>
              <button
                onClick={() => setShot(null)}
                className="flex items-center gap-1.5 rounded-sm border border-graphite-600 px-3.5 py-2 text-xs text-ink-300 hover:bg-graphite-700"
              >
                <RotateCcw size={13} />
                Retake
              </button>
              <button
                onClick={handleUsePhoto}
                className="flex items-center gap-1.5 rounded-sm bg-amber-500 px-3.5 py-2 text-xs font-medium text-graphite-950 hover:bg-amber-400"
              >
                <Check size={13} strokeWidth={2} />
                Use this photo
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}