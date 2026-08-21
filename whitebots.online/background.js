(() => {
  const canvas = document.getElementById('bgWave');
  if (!canvas) return;

  const context = canvas.getContext('2d', { alpha: false });
  const characters = ' .:-=+*#%@';
  const palette = ['#171717', '#2a2a2a', '#454545', '#6a6a6a'];
  const fontSize = 16;
  const cellWidth = 12;
  const cellHeight = 18;
  const frameInterval = 1000 / 30;
  let width = 0;
  let height = 0;
  let columns = 0;
  let rows = 0;
  let lastFrame = 0;
  let animationFrame;

  function resize() {
    const devicePixelRatio = Math.min(window.devicePixelRatio || 1, 1.25);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.ceil(width * devicePixelRatio);
    canvas.height = Math.ceil(height * devicePixelRatio);
    context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    columns = Math.ceil(width / cellWidth);
    rows = Math.ceil(height / cellHeight);
  }

  function waveValue(x, y, time) {
    return Math.sin(x * 0.055 + time * 1.1) * 0.55
      + Math.sin(y * 0.09 - time * 0.8 + x * 0.018) * 0.3
      + Math.sin(Math.sqrt(x * x + y * y) * 0.025 - time * 0.65) * 0.35
      + Math.sin(x * 0.025 + y * 0.04 + time * 1.5) * 0.15;
  }

  function draw(time) {
    if (document.hidden) {
      animationFrame = undefined;
      return;
    }

    animationFrame = requestAnimationFrame(draw);
    if (time - lastFrame < frameInterval) return;
    lastFrame = time;

    context.fillStyle = '#0a0a0a';
    context.fillRect(0, 0, width, height);
    context.font = `${fontSize}px Menlo, Monaco, Consolas, monospace`;
    context.textBaseline = 'top';
    const waveTime = Date.now() * 0.001;

    for (let row = 0; row < rows; row += 1) {
      for (let column = 0; column < columns; column += 1) {
        const intensity = Math.min(Math.abs(waveValue(column, row, waveTime)) * 1.7, 1);
        if (intensity < 0.12) continue;
        const characterIndex = Math.min(characters.length - 1, Math.floor(intensity * characters.length));
        const character = characters[characterIndex];
        if (character === ' ') continue;
        context.fillStyle = palette[Math.min(palette.length - 1, Math.floor(intensity * palette.length))];
        context.fillText(character, column * cellWidth, row * cellHeight);
      }
    }
  }

  function resume() {
    if (!document.hidden && animationFrame === undefined) {
      lastFrame = 0;
      animationFrame = requestAnimationFrame(draw);
    }
  }

  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('visibilitychange', resume);
  resize();
  resume();
})();
