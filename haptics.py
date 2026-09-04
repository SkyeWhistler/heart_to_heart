
import numpy as np
import sounddevice as sd




def _resolve_device(spec):
    """Return an output device index from an int index or a name substring.

    Returns None (the system default output) if a name can't be matched, so the
    engine still runs for SIMULATE testing with no speakers connected.
    """
    if spec is None or isinstance(spec, int):
        return spec
    name = str(spec).lower()
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0 and name in dev["name"].lower():
            return idx
    print(f"[haptics] WARNING: no output device matching '{spec}' ")
    return None


class _Voice:
    """One independent output stream feeding one speaker its own pulse train."""

    def __init__(self, device, amp, freq, dur, decay):
        self.device = device
        try:
            info = sd.query_devices(device, "output")
            self.fs = int(info["default_samplerate"]) or 44100
            self.ch = min(2, info["max_output_channels"]) or 1
            self.name = info["name"]
        except Exception:
            self.fs, self.ch, self.name = 44100, 2, "default"

        # Pre-render one heartbeat "thump" at this device's sample rate, scaled by this speaker's calibrated amplitude.
        n = int(self.fs * dur)
        t = np.arange(n) / self.fs
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)
        peak = np.max(np.abs(wave))
        if peak > 0:
            wave = wave / peak
        self.pulse = (wave * min(amp, 1.0)).astype(np.float32)

        self.spb = float(self.fs)              # samples per beat (60 BPM default)
        self._acc = 0.0                        # samples until next beat
        self._pos = len(self.pulse)            # >= len means "no active pulse"
        self.gain = 0.0                        # gate: 0 off, 1 on

        self.stream = sd.OutputStream(
            samplerate=self.fs, device=device, channels=self.ch,
            dtype="float32", callback=self._callback,
        )
        self.stream.start()

    def _callback(self, outdata, frames, time_info, status):
        buf = np.zeros(frames, dtype=np.float32)
        plen = len(self.pulse)
        pos, acc, spb = self._pos, self._acc, self.spb
        i = 0
        while i < frames:
            rem = frames - i
            if pos < plen:
                k = min(rem, plen - pos)
                buf[i:i + k] += self.pulse[pos:pos + k]
                pos += k
                i += k
            elif acc <= 0:
                pos = 0
                acc += spb
            else:
                step = int(min(rem, acc)) or 1
                acc -= step
                i += step
        self._pos, self._acc = pos, acc
        outdata[:] = np.repeat((buf * self.gain)[:, None], self.ch, axis=1)

    def set_bpm(self, bpm):
        if bpm and bpm > 0:
            self.spb = self.fs * 60.0 / bpm

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass


class Haptics:
    """Two-speaker haptic engine."""

    def __init__(self, device_a="Humbird", device_b="Vibro",
                 amp_a=0.90, amp_b=0.75,
                 freq=90.0, dur=0.14, decay=0.04):
        idx_a = _resolve_device(device_a)
        idx_b = _resolve_device(device_b)
        self.voices = [
            _Voice(idx_a, amp_a, freq, dur, decay),   # device 0 
            _Voice(idx_b, amp_b, freq, dur, decay),   # device 1 
        ]
        print(f"[haptics] device 0 (LEFT)  -> {self.voices[0].name}  amp {amp_a}")
        print(f"[haptics] device 1 (RIGHT) -> {self.voices[1].name}  amp {amp_b}")

    # -- control -----------------------
    def set_bpm(self, channel, bpm):
        """Set the pulse rate for one device (0 or 1) from a BPM."""
        self.voices[channel].set_bpm(bpm)

    def on(self):
        """Haptic-on phase: pulses become felt on both speakers."""
        for v in self.voices:
            v.gain = 1.0

    def off(self):
        """Haptic-off phase: silent (engine keeps running)."""
        for v in self.voices:
            v.gain = 0.0

    def close(self):
        for v in self.voices:
            v.close()
