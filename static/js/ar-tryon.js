/**
 * AR Virtual Try-On
 * - Face mode : sunglasses, hats → MediaPipe FaceMesh
 * - Body mode : clothing         → MediaPipe Pose
 */

let tryOnActive = false;
let videoStream = null;
let animFrameId = null;
let poseInst = null;
let faceInst = null;
let currentImage = null;
let currentMode = "body";

const FACE_KEYWORDS = [
  "sunglasses",
  "eyewear",
  "glasses",
  "sunglass",
  "hat",
  "cap",
];

// ── Entry point ───────────────────────────────────────────────
function openTryOn(imageUrl, productName, categoryName) {
  const cat = (categoryName || "").toLowerCase().trim();
  currentMode = FACE_KEYWORDS.some((k) => cat.includes(k)) ? "face" : "body";

  // Accept array or single string — for face mode use last image (isolated product shot)
  const urls = Array.isArray(imageUrl) ? imageUrl : [imageUrl];
  const chosenUrl = currentMode === "face" ? urls[urls.length - 1] : urls[0];

  console.log(
    "[TryOn] category:",
    cat,
    "→ mode:",
    currentMode,
    "| url:",
    chosenUrl,
  );

  if (!document.getElementById("tryOnModal")) buildModal();

  loadProductImage(chosenUrl);

  document.getElementById("tryOnProductName").textContent =
    productName || "Product";
  document.getElementById("tryOnModeLabel").textContent =
    currentMode === "face" ? "😎 Face mode" : "👕 Body mode";

  document.getElementById("tryOnModal").style.display = "flex";
  document.body.style.overflow = "hidden";
  startCamera();
}

function loadProductImage(url) {
  if (!url) return;

  if (currentMode === "face") {
    // Use remove.bg API to strip background for clean face overlay
    const status = document.getElementById("tryOnStatus");
    if (status)
      status.innerHTML =
        '<i class="fas fa-magic fa-spin me-1"></i> Removing background...';

    const formData = new FormData();
    // Build absolute URL for the image
    const absUrl = url.startsWith("http") ? url : window.location.origin + url;
    formData.append("image_url", absUrl);

    fetch("/remove-background/", {
      method: "POST",
      body: formData,
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    })
      .then((r) => r.json())
      .then((data) => {
        console.log("[TryOn] remove.bg response:", data);
        if (data.success) {
          currentImage = new Image();
          currentImage.onload = () => {
            if (status)
              status.innerHTML =
                '<i class="fas fa-check-circle me-1" style="color:#4caf50;"></i> Try-On active!';
            console.log("[TryOn] BG-removed image ready");
          };
          currentImage.src = data.image; // base64 PNG with transparent bg
        } else {
          console.warn("[TryOn] remove.bg failed, using canvas strip:", data.error);
          loadRawImageWithStrip(url);
        }
      })
      .catch((err) => {
        console.error("[TryOn] remove.bg fetch error:", err);
        loadRawImageWithStrip(url);
      });
  } else {
    loadRawImage(url);
  }
}

function loadRawImage(url) {
  currentImage = new Image();
  currentImage.crossOrigin = "anonymous";
  currentImage.onload = () => console.log("[TryOn] Raw image loaded");
  currentImage.onerror = () => console.error("[TryOn] Image load failed:", url);
  currentImage.src = url;
}

// Fallback: load image then strip background via canvas pixel manipulation
function loadRawImageWithStrip(url) {
  const tmp = new Image();
  tmp.crossOrigin = "anonymous";
  tmp.onload = () => {
    const stripped = stripBackground(tmp);
    // Convert canvas to Image object
    currentImage = new Image();
    currentImage.onload = () => console.log("[TryOn] Canvas-stripped image ready");
    currentImage.src = stripped.toDataURL('image/png');
    const status = document.getElementById("tryOnStatus");
    if (status) status.innerHTML = '<i class="fas fa-check-circle me-1" style="color:#4caf50;"></i> Try-On active!';
  };
  tmp.onerror = () => console.error("[TryOn] Image load failed:", url);
  tmp.src = url;
}

function getCookie(name) {
  const v = document.cookie.match("(^|;) ?" + name + "=([^;]*)(;|$)");
  return v ? v[2] : "";
}
function closeTryOn() {
  stopCamera();
  const m = document.getElementById("tryOnModal");
  if (m) m.style.display = "none";
  document.body.style.overflow = "";
}

// ── Modal ─────────────────────────────────────────────────────
function buildModal() {
  const modal = document.createElement("div");
  modal.id = "tryOnModal";
  modal.style.cssText = `
        display:none;position:fixed;inset:0;z-index:9999;
        background:rgba(0,0,0,0.93);flex-direction:column;
        align-items:center;justify-content:center;`;
  modal.innerHTML = `
        <div style="position:relative;width:100%;max-width:640px;padding:0 12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div>
                    <span style="color:#fff;font-size:1.1rem;font-weight:700;">
                        <i class="fas fa-camera" style="color:#456273;"></i> AR Virtual Try-On
                    </span><br>
                    <span id="tryOnProductName" style="color:#ccc;font-size:0.85rem;"></span>
                    <span id="tryOnModeLabel"   style="color:#aaa;font-size:0.75rem;margin-left:8px;"></span>
                </div>
                <button onclick="closeTryOn()"
                    style="background:none;border:none;color:#fff;font-size:1.5rem;cursor:pointer;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div style="position:relative;border-radius:14px;overflow:hidden;background:#111;">
                <video id="tryOnVideo" autoplay playsinline muted
                    style="width:100%;display:block;transform:scaleX(-1);"></video>
                <canvas id="tryOnCanvas"
                    style="position:absolute;top:0;left:0;width:100%;height:100%;transform:scaleX(-1);"></canvas>
                <div id="tryOnStatus" style="
                    position:absolute;bottom:12px;left:50%;transform:translateX(-50%);
                    background:rgba(0,0,0,0.65);color:#fff;padding:6px 16px;
                    border-radius:20px;font-size:0.8rem;white-space:nowrap;">
                    <i class="fas fa-spinner fa-spin me-1"></i> Starting...
                </div>
            </div>
            <div style="color:#666;font-size:0.75rem;text-align:center;margin-top:8px;">
                Face mode: look straight at camera, 50–80 cm away · Body mode: stand 1–2 m back
            </div>
        </div>`;
  document.body.appendChild(modal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeTryOn();
  });
}

// ── Camera ────────────────────────────────────────────────────
async function startCamera() {
  const video = document.getElementById("tryOnVideo");
  const status = document.getElementById("tryOnStatus");
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 640 },
        height: { ideal: 480 },
      },
      audio: false,
    });
    video.srcObject = videoStream;
    await video.play();

    status.innerHTML =
      '<i class="fas fa-circle-notch fa-spin me-1"></i> Loading model...';

    if (currentMode === "face") {
      await initFaceMesh();
    } else {
      await initPose();
    }

    status.innerHTML =
      '<i class="fas fa-check-circle me-1" style="color:#4caf50;"></i> Try-On active!';
    tryOnActive = true;
    renderLoop();
  } catch (err) {
    console.error("[TryOn] Error:", err);
    status.innerHTML = `<i class="fas fa-exclamation-triangle me-1" style="color:#f44336;"></i> ${err.message}`;
  }
}

function stopCamera() {
  tryOnActive = false;
  if (animFrameId) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }
  if (videoStream) {
    videoStream.getTracks().forEach((t) => t.stop());
    videoStream = null;
  }
}

// ── Init FaceMesh ─────────────────────────────────────────────
function initFaceMesh() {
  return new Promise((resolve, reject) => {
    if (faceInst) {
      resolve();
      return;
    }

    if (typeof FaceMesh === "undefined") {
      reject(new Error("FaceMesh library not loaded. Please refresh."));
      return;
    }

    faceInst = new FaceMesh({
      locateFile: (f) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`,
    });
    faceInst.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    faceInst.onResults(drawFaceOverlay);
    faceInst.initialize().then(resolve).catch(reject);
  });
}

// ── Init Pose ─────────────────────────────────────────────────
function initPose() {
  return new Promise((resolve, reject) => {
    if (poseInst) {
      resolve();
      return;
    }

    if (typeof Pose === "undefined") {
      reject(new Error("Pose library not loaded. Please refresh."));
      return;
    }

    poseInst = new Pose({
      locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}`,
    });
    poseInst.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    poseInst.onResults(drawBodyOverlay);
    poseInst.initialize().then(resolve).catch(reject);
  });
}

// ── Render loop ───────────────────────────────────────────────
function renderLoop() {
  if (!tryOnActive) return;
  const video = document.getElementById("tryOnVideo");
  if (video && video.readyState >= 2) {
    if (currentMode === "face" && faceInst) {
      faceInst.send({ image: video }).catch(() => {});
    } else if (currentMode === "body" && poseInst) {
      poseInst.send({ image: video }).catch(() => {});
    }
  }
  animFrameId = requestAnimationFrame(renderLoop);
}

// ── Remove background from product image ─────────────────────
// Strips dark, white, and light-gray backgrounds pixel by pixel
function stripBackground(img) {
  const off = document.createElement("canvas");
  off.width = img.naturalWidth;
  off.height = img.naturalHeight;
  const octx = off.getContext("2d");
  octx.drawImage(img, 0, 0);

  const id = octx.getImageData(0, 0, off.width, off.height);
  const data = id.data;

  // Sample corner pixels to detect background color
  const corners = [
    [data[0], data[1], data[2]], // top-left
    [
      data[(off.width - 1) * 4],
      data[(off.width - 1) * 4 + 1],
      data[(off.width - 1) * 4 + 2],
    ], // top-right
    [
      data[(off.height - 1) * off.width * 4],
      data[(off.height - 1) * off.width * 4 + 1],
      data[(off.height - 1) * off.width * 4 + 2],
    ], // bottom-left
  ];
  const bgR = corners[0][0],
    bgG = corners[0][1],
    bgB = corners[0][2];

  for (let i = 0; i < data.length; i += 4) {
    const r = data[i],
      g = data[i + 1],
      b = data[i + 2];

    // Remove pixels close to detected background color
    const matchesBg =
      Math.abs(r - bgR) < 30 &&
      Math.abs(g - bgG) < 30 &&
      Math.abs(b - bgB) < 30;
    // Always remove near-black
    const isBlack = r < 35 && g < 35 && b < 35;
    // Always remove near-white
    const isWhite = r > 235 && g > 235 && b > 235;
    // Remove uniform gray
    const isGray = Math.abs(r - g) < 12 && Math.abs(g - b) < 12 && r > 180;

    if (matchesBg || isBlack || isWhite || isGray) {
      data[i + 3] = 0;
    }
  }

  octx.putImageData(id, 0, 0);
  return off;
}

// ── Draw sunglasses on face using actual product image ────────
function drawFaceOverlay(results) {
  const canvas = document.getElementById("tryOnCanvas");
  const video = document.getElementById("tryOnVideo");

  if (!canvas || !video) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!results.multiFaceLandmarks || !results.multiFaceLandmarks.length) return;
  if (!currentImage || !currentImage.complete || !currentImage.naturalWidth)
    return;

  const lm = results.multiFaceLandmarks[0];

  const W = canvas.width;
  const H = canvas.height;

  // ── Stable eye landmarks
  const leftEye = lm[33];
  const rightEye = lm[263];

  if (!leftEye || !rightEye) return;

  const lX = leftEye.x * W;
  const lY = leftEye.y * H;

  const rX = rightEye.x * W;
  const rY = rightEye.y * H;

  // ── Eye distance
  const eyeDist = Math.hypot(rX - lX, rY - lY);

  // ── Glasses scaling
  const glassesW = eyeDist * 2.2;
  const aspect = currentImage.naturalHeight / currentImage.naturalWidth;
  const glassesH = glassesW * aspect;

  // ── Glasses center
  const centerX = (lX + rX) / 2;
  const centerY = (lY + rY) / 2;

  // ── Head tilt rotation
  const angle = Math.atan2(rY - lY, rX - lX);

  ctx.save();

  // move origin to eyes center
  ctx.translate(centerX, centerY);

  // rotate glasses
  ctx.rotate(angle);

  ctx.globalAlpha = 0.95;

  // draw glasses
  ctx.drawImage(
    currentImage,
    -glassesW / 2,
    -glassesH * 0.45,
    glassesW,
    glassesH,
  );

  ctx.restore();
}

// ── Draw clothing on body ─────────────────────────────────────
function drawBodyOverlay(results) {
  const canvas = document.getElementById("tryOnCanvas");
  const video = document.getElementById("tryOnVideo");
  if (!canvas || !video) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!results.poseLandmarks) return;
  if (!currentImage || !currentImage.complete || !currentImage.naturalWidth)
    return;

  const lm = results.poseLandmarks;
  const W = canvas.width;
  const H = canvas.height;

  const ls = lm[11];
  const rs = lm[12];
  const lh = lm[23];
  const rh = lm[24];
  if (!ls || !rs || !lh || !rh) return;

  // Canvas is CSS-mirrored so use raw coords
  const lsX = ls.x * W;
  const lsY = ls.y * H;
  const rsX = rs.x * W;
  const rsY = rs.y * H;
  const lhY = lh.y * H;
  const rhY = rh.y * H;

  const shoulderW = Math.abs(lsX - rsX);
  const torsoH = Math.abs((lhY + rhY) / 2 - (lsY + rsY) / 2);
  const garmentW = shoulderW * 1.5;
  const garmentH = torsoH * 1.6;
  const centerX = (lsX + rsX) / 2;
  const topY = Math.min(lsY, rsY) - garmentH * 0.08;

  ctx.save();
  ctx.globalAlpha = 0.82;
  ctx.drawImage(currentImage, centerX - garmentW / 2, topY, garmentW, garmentH);
  ctx.restore();
}

// ── Switch product ────────────────────────────────────────────
function switchTryOnProduct(imageUrl, name, categoryName) {
  const cat = (categoryName || "").toLowerCase().trim();
  const newMode = FACE_KEYWORDS.some((k) => cat.includes(k)) ? "face" : "body";

  loadProductImage(imageUrl);
  document.getElementById("tryOnProductName").textContent = name;
  document.getElementById("tryOnModeLabel").textContent =
    newMode === "face" ? "😎 Face mode" : "👕 Body mode";

  if (newMode !== currentMode) {
    currentMode = newMode;
    const status = document.getElementById("tryOnStatus");
    status.innerHTML =
      '<i class="fas fa-circle-notch fa-spin me-1"></i> Switching model...';
    (currentMode === "face" ? initFaceMesh() : initPose()).then(() => {
      status.innerHTML =
        '<i class="fas fa-check-circle me-1" style="color:#4caf50;"></i> Try-On active!';
    });
  } else {
    currentMode = newMode;
  }
}