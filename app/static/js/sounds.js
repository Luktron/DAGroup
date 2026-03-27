/**
 * Sound engine — generates all sounds via Web Audio API (no external files needed).
 */
const SoundFX = (() => {
    let ctx;

    function getCtx() {
        if (!ctx) {
            ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        return ctx;
    }

    function playTone(freq, duration, type = 'sine', volume = 0.15) {
        try {
            const c = getCtx();
            const osc = c.createOscillator();
            const gain = c.createGain();
            osc.type = type;
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(volume, c.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, c.currentTime + duration);
            osc.connect(gain);
            gain.connect(c.destination);
            osc.start();
            osc.stop(c.currentTime + duration);
        } catch (e) { /* Audio not available */ }
    }

    return {
        death() {
            playTone(200, 0.8, 'sawtooth', 0.12);
            setTimeout(() => playTone(120, 1.2, 'sawtooth', 0.08), 200);
        },
        kill() {
            playTone(800, 0.15, 'square', 0.08);
            setTimeout(() => playTone(400, 0.3, 'square', 0.05), 100);
        },
        investigate() {
            playTone(600, 0.2, 'sine', 0.08);
            setTimeout(() => playTone(900, 0.3, 'sine', 0.06), 150);
        },
        accuse() {
            playTone(500, 0.15, 'sawtooth', 0.1);
            setTimeout(() => playTone(700, 0.15, 'sawtooth', 0.1), 100);
            setTimeout(() => playTone(1000, 0.4, 'sawtooth', 0.08), 200);
        },
        success() {
            playTone(523, 0.2, 'sine', 0.1);
            setTimeout(() => playTone(659, 0.2, 'sine', 0.1), 150);
            setTimeout(() => playTone(784, 0.4, 'sine', 0.1), 300);
        },
        error() {
            playTone(300, 0.3, 'square', 0.08);
            setTimeout(() => playTone(200, 0.5, 'square', 0.06), 200);
        },
        look() {
            playTone(1200, 0.08, 'sine', 0.04);
        },
        chat() {
            playTone(1000, 0.05, 'sine', 0.03);
        },
        blackout() {
            playTone(80, 2.0, 'sawtooth', 0.15);
            setTimeout(() => playTone(60, 1.5, 'sawtooth', 0.1), 500);
        },
        tension() {
            playTone(100, 3.0, 'sine', 0.03);
        },
        gameOver() {
            playTone(400, 0.3, 'sine', 0.12);
            setTimeout(() => playTone(350, 0.3, 'sine', 0.1), 250);
            setTimeout(() => playTone(300, 0.5, 'sine', 0.08), 500);
            setTimeout(() => playTone(200, 1.0, 'sine', 0.06), 800);
        },
        victory() {
            [523, 659, 784, 1047].forEach((f, i) => {
                setTimeout(() => playTone(f, 0.3, 'sine', 0.1), i * 150);
            });
        },
    };
})();
