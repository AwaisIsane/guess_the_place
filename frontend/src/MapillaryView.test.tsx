// @vitest-environment jsdom

import { StrictMode, act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

type ViewerDouble = {
  canvas: HTMLCanvasElement;
  moveTo: ReturnType<typeof vi.fn>;
  remove: ReturnType<typeof vi.fn>;
};

const viewerState = vi.hoisted(() => ({
  instances: [] as ViewerDouble[],
  moveFailures: [] as Error[],
}));

vi.mock("mapillary-js", () => {
  class CancelMapillaryError extends Error {}

  class Viewer {
    canvas: HTMLCanvasElement;
    moveTo = vi.fn((imageId: string) => {
      const failure = viewerState.moveFailures.shift();
      return failure ? Promise.reject(failure) : Promise.resolve({ id: imageId });
    });
    remove = vi.fn();

    constructor({ container }: { container: HTMLElement }) {
      this.canvas = document.createElement("canvas");
      container.append(this.canvas);
      viewerState.instances.push(this);
    }
  }

  return { CancelMapillaryError, Viewer };
});

import { MapillaryView } from "./MapillaryView";

type Rendered = { container: HTMLDivElement; root: Root };

async function renderView(imageId = "image-one", strict = false): Promise<Rendered> {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  const view = <MapillaryView imageId={imageId} accessToken="client-token" />;
  await act(async () => {
    root.render(strict ? <StrictMode>{view}</StrictMode> : view);
    await Promise.resolve();
  });
  return { container, root };
}

async function unmount({ container, root }: Rendered) {
  await act(async () => root.unmount());
  container.remove();
}

describe("MapillaryView", () => {
  const rendered: Rendered[] = [];

  beforeAll(() => {
    (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
      .IS_REACT_ACT_ENVIRONMENT = true;
  });

  beforeEach(() => {
    viewerState.instances.length = 0;
    viewerState.moveFailures.length = 0;
  });

  afterEach(async () => {
    while (rendered.length) await unmount(rendered.pop()!);
    vi.restoreAllMocks();
  });

  it("creates one effective viewer during the StrictMode effect replay", async () => {
    rendered.push(await renderView("image-one", true));

    expect(viewerState.instances).toHaveLength(1);
    expect(viewerState.instances[0].moveTo).toHaveBeenCalledWith("image-one");
  });

  it("moves the existing viewer when the image changes", async () => {
    const mounted = await renderView();
    rendered.push(mounted);

    await act(async () => {
      mounted.root.render(<MapillaryView imageId="image-two" accessToken="client-token" />);
      await Promise.resolve();
    });

    expect(viewerState.instances).toHaveLength(1);
    expect(viewerState.instances[0].moveTo).toHaveBeenNthCalledWith(2, "image-two");
  });

  it("recreates the viewer once after unexpected WebGL context loss", async () => {
    const mounted = await renderView();
    rendered.push(mounted);
    const contextLost = new Event("webglcontextlost", { cancelable: true });

    await act(async () => {
      viewerState.instances[0].canvas.dispatchEvent(contextLost);
      await new Promise((resolve) => window.setTimeout(resolve, 120));
      await Promise.resolve();
    });

    expect(contextLost.defaultPrevented).toBe(true);
    expect(viewerState.instances[0].remove).toHaveBeenCalledOnce();
    expect(viewerState.instances).toHaveLength(2);
    expect(viewerState.instances[1].moveTo).toHaveBeenCalledWith("image-one");
  });

  it("shows a retry action when image loading fails", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    viewerState.moveFailures.push(new Error("image unavailable"));
    const mounted = await renderView();
    rendered.push(mounted);

    expect(mounted.container.textContent).toContain("Imagery preview unavailable");
    expect(mounted.container.querySelector("button")?.textContent).toBe("Retry street view");

    await act(async () => {
      mounted.container.querySelector("button")?.click();
      await Promise.resolve();
    });

    expect(viewerState.instances).toHaveLength(2);
    expect(mounted.container.textContent).not.toContain("Imagery preview unavailable");
  });
});
