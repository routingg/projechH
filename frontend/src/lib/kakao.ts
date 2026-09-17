// 카카오맵 JavaScript SDK 공용 로더
export const KAKAO_KEY = import.meta.env.VITE_KAKAO_MAP_KEY as string | undefined;

// 제주국제공항 좌표
export const JEJU_AIRPORT = { lat: 33.5104, lng: 126.4914 };

declare global {
  interface Window {
    kakao: any;
  }
}

let sdkPromise: Promise<any> | null = null;

/** Kakao SDK 를 1회만 로드하고 window.kakao 를 resolve. */
export function loadKakaoSdk(): Promise<any> {
  if (!KAKAO_KEY) return Promise.reject(new Error("no-key"));
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise((resolve, reject) => {
    if (window.kakao?.maps) return resolve(window.kakao);
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_KEY}&autoload=false`;
    script.onload = () => window.kakao.maps.load(() => resolve(window.kakao));
    script.onerror = () => reject(new Error("load-fail"));
    document.head.appendChild(script);
  });
  return sdkPromise;
}
