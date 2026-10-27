import type { BoundingBox } from "@/types";

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Rect of the rendered media inside its container when scaled with
 * `object-fit: contain` (i.e. excluding letterbox / pillarbox bars).
 */
export function getContentRect(
  containerW: number,
  containerH: number,
  mediaW: number,
  mediaH: number,
): Rect {
  if (containerW <= 0 || containerH <= 0 || mediaW <= 0 || mediaH <= 0) {
    return { left: 0, top: 0, width: containerW, height: containerH };
  }
  const scale = Math.min(containerW / mediaW, containerH / mediaH);
  const width = mediaW * scale;
  const height = mediaH * scale;
  return {
    left: (containerW - width) / 2,
    top: (containerH - height) / 2,
    width,
    height,
  };
}

/** Maps a normalised box to container pixel coordinates. */
export function mapBox(box: BoundingBox, content: Rect): Rect {
  return {
    left: content.left + box.x * content.width,
    top: content.top + box.y * content.height,
    width: box.w * content.width,
    height: box.h * content.height,
  };
}
