// Click any icon/scene/diagram image to see it large (owner: "ik kan niet zoomen").
// Arrows / swipe browse, Esc or tap closes. Pinch-zoom works natively in the overlay.
;(() => {
  const css = `.zx{position:fixed;inset:0;z-index:99;background:rgba(14,22,38,.86);display:grid;place-items:center;touch-action:pinch-zoom}
.zx img{width:min(92vw,84vh);height:min(92vw,84vh);max-width:96vw;max-height:88vh;object-fit:contain;background:var(--mode-bg,#f6f3ee);border-radius:16px}
.zx b{position:fixed;bottom:14px;left:0;right:0;text-align:center;color:#f6f3ee;font:600 14px system-ui}
main img,.wrap img{cursor:zoom-in}`
  document.head.insertAdjacentHTML("beforeend", `<style>${css}</style>`)
  let list = [],
    i = 0,
    box = null
  const big = (src) => src.replace(/\/(icon|flat)\/(light|dark)\//, "/$1/$2/")
  const show = () => {
    const im = list[i]
    box.innerHTML = `<img src="${big(im.currentSrc || im.src)}" alt=""><b>${im.alt || ""} · ${i + 1}/${list.length}</b>`
  }
  const close = () => {
    box?.remove()
    box = null
  }
  document.addEventListener("click", (e) => {
    const im = e.target.closest("img")
    if (box) return close()
    if (!im || im.closest("nav") || im.width < 40) return
    list = [...document.querySelectorAll("img")].filter((x) => x.width >= 40 && !x.closest("nav"))
    i = list.indexOf(im)
    box = document.createElement("div")
    box.className = "zx"
    document.body.append(box)
    show()
  })
  document.addEventListener("keydown", (e) => {
    if (!box) return
    if (e.key === "Escape") close()
    if (e.key === "ArrowRight") {
      i = (i + 1) % list.length
      show()
    }
    if (e.key === "ArrowLeft") {
      i = (i - 1 + list.length) % list.length
      show()
    }
  })
  let x0 = null
  document.addEventListener(
    "touchstart",
    (e) => {
      if (box && e.touches.length === 1) x0 = e.touches[0].clientX
    },
    { passive: true },
  )
  document.addEventListener("touchend", (e) => {
    if (!box || x0 === null) return
    const dx = e.changedTouches[0].clientX - x0
    x0 = null
    if (Math.abs(dx) > 50) {
      i = (i + (dx < 0 ? 1 : -1) + list.length) % list.length
      show()
      e.preventDefault()
    }
  })
})()
