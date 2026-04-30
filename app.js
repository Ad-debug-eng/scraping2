function renderCards(trackEl, items) {
  // Render ONLY the real items (10 max). Carousel logic will recycle nodes.
  trackEl.innerHTML = items
    .map(
      (item) => `
        <article class="release-card">
          <div class="poster-wrap">
            <img src="${item.image}" alt="${item.title}" loading="lazy" />
          </div>
          <div class="card-body">
            <h2 class="title">${item.title}</h2>
            <p class="provider">${item.provider}</p>
          </div>
        </article>
      `
    )
    .join("");
}

function setupInfiniteCarousel({ viewportEl, trackEl, itemCount }) {
  // Seamless infinite loop with ONLY N real cards:
  // move track via translateX; when the first card fully leaves left,
  // move it to the end and adjust offset so motion feels continuous.
  let rafId = null;
  const autoSpeedPxPerFrame = 0.45; // slightly slower continuous speed
  let offsetX = 0;
  let isDragging = false;
  let dragStartX = 0;
  let dragStartOffset = 0;

  function getGap() {
    const style = getComputedStyle(trackEl);
    return parseFloat(style.columnGap || style.gap || "14") || 14;
  }

  function getStep() {
    const firstCard = trackEl.querySelector(".release-card");
    if (!firstCard) return 240;
    return firstCard.getBoundingClientRect().width + getGap();
  }

  function applyTransform() {
    trackEl.style.transform = `translate3d(${offsetX}px, 0, 0)`;
  }

  function recycleLeftIfNeeded() {
    const step = getStep();
    // When we've moved left by 1+ card widths, rotate nodes.
    while (offsetX <= -step) {
      const first = trackEl.firstElementChild;
      if (!first) break;
      trackEl.appendChild(first);
      offsetX += step;
    }
  }

  function recycleRightIfNeeded() {
    const step = getStep();
    while (offsetX >= step) {
      const last = trackEl.lastElementChild;
      if (!last) break;
      trackEl.insertBefore(last, trackEl.firstElementChild);
      offsetX -= step;
    }
  }

  function tick() {
    if (!isDragging) {
      offsetX -= autoSpeedPxPerFrame;
      recycleLeftIfNeeded();
      applyTransform();
    }
    rafId = requestAnimationFrame(tick);
  }

  function onPointerDown(e) {
    isDragging = true;
    dragStartX = e.clientX;
    dragStartOffset = offsetX;
    viewportEl.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e) {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    offsetX = dragStartOffset + dx;
    // Keep offset bounded by recycling both directions during drag
    recycleLeftIfNeeded();
    recycleRightIfNeeded();
    applyTransform();
  }

  function onPointerUp(e) {
    if (!isDragging) return;
    isDragging = false;
    try {
      viewportEl.releasePointerCapture(e.pointerId);
    } catch {
      // ignore
    }
  }

  viewportEl.addEventListener("pointerdown", onPointerDown);
  viewportEl.addEventListener("pointermove", onPointerMove);
  viewportEl.addEventListener("pointerup", onPointerUp);
  viewportEl.addEventListener("pointercancel", onPointerUp);

  applyTransform();
  rafId = requestAnimationFrame(tick);

  return {
    next() {
      // Advance by one card (to the left).
      offsetX -= getStep();
      recycleLeftIfNeeded();
      applyTransform();
    },
    prev() {
      // Go back by one card (to the right).
      offsetX += getStep();
      recycleRightIfNeeded();
      applyTransform();
    },
    stop() {
      if (rafId) cancelAnimationFrame(rafId);
      rafId = null;
    },
  };
}

async function loadSection({ url, limit, trackId }) {
  const trackEl = document.getElementById(trackId);
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  const items = Array.isArray(data) ? data.slice(0, limit) : [];
  renderCards(trackEl, items);
  return items.length;
}

async function loadUpdates() {
  const statusEl = document.getElementById("status");

  try {
    const trendingCount = await loadSection({
      url: "ott_trending.json",
      limit: 10,
      trackId: "track",
    });

    const popularCount = await loadSection({
      url: "ott_popular.json",
      limit: 10,
      trackId: "popularTrack",
    });

    const trendingCarousel = setupInfiniteCarousel({
      viewportEl: document.getElementById("trendingViewport"),
      trackEl: document.getElementById("track"),
      itemCount: trendingCount,
    });

    const popularCarousel = setupInfiniteCarousel({
      viewportEl: document.getElementById("popularViewport"),
      trackEl: document.getElementById("popularTrack"),
      itemCount: popularCount,
    });

    // Hook up buttons
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      const target = btn.getAttribute("data-target");
      const isLeft = btn.classList.contains("nav-btn--left");
      const carousel = target === "popular" ? popularCarousel : trendingCarousel;
      btn.addEventListener("click", () => (isLeft ? carousel.prev() : carousel.next()));
    });

    statusEl.textContent = `Trending: ${trendingCount} • Most popular: ${popularCount} (swipe/drag or use arrows)`;
  } catch (error) {
    statusEl.textContent =
      "Could not load JSON files. Start a local server in this folder and generate the JSON.";
    document.getElementById("track").innerHTML = "";
    document.getElementById("popularTrack").innerHTML = "";
    console.error(error);
  }
}

loadUpdates();
