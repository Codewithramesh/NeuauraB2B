import { describe, it, expect, vi, afterEach } from "vitest";
import { BrowserMicrophoneAdapter, UploadedAudioAdapter } from "./audio";
import { durationLabel, human } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("audio capture adapters", () => {
  it("keeps real uploaded bytes and source metadata", () => {
    const file = new File(["real file bytes"], "guest.wav", {
      type: "audio/wav",
    });
    const result = new UploadedAudioAdapter(file).submission();
    expect(result.blob).toBe(file);
    expect(result.sourceType).toBe("upload");
    expect(result.mime).toBe("audio/wav");
  });
  it("does not request microphone access during construction", () => {
    const permission = vi.fn();
    vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: permission } });
    new BrowserMicrophoneAdapter();
    expect(permission).not.toHaveBeenCalled();
  });
  it("rejects a recording in an insecure context without opening the microphone", async () => {
    vi.stubGlobal("isSecureContext", false);
    const adapter = new BrowserMicrophoneAdapter();
    await expect(adapter.start()).rejects.toThrow("trusted HTTPS");
  });
  it("does not pretend captured audio exists", () => {
    expect(() => new BrowserMicrophoneAdapter().submission()).toThrow(
      "Stop the recording",
    );
  });
  it("cleans up microphone tracks when recorder initialization fails", async () => {
    vi.stubGlobal("isSecureContext", true);
    const stop = vi.fn();
    vi.stubGlobal("navigator", {
      mediaDevices: {
        getUserMedia: vi
          .fn()
          .mockResolvedValue({ getTracks: () => [{ stop }] }),
      },
    });
    class Broken {
      static isTypeSupported() {
        return true;
      }
      constructor() {
        throw new Error("Cannot record");
      }
    }
    vi.stubGlobal("MediaRecorder", Broken);
    await expect(new BrowserMicrophoneAdapter().start()).rejects.toThrow(
      "Cannot record",
    );
    expect(stop).toHaveBeenCalled();
  });
});
describe("readable time and states", () => {
  it("formats duration beyond a minute", () =>
    expect(durationLabel(125.6)).toBe("02:05"));
  it("renders explicit failure states", () =>
    expect(human("model_missing")).toBe("Model missing"));
});
