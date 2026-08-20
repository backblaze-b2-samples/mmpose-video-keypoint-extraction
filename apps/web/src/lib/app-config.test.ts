import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("MMPose Video Keypoint Extraction");
    expect(APP_DESCRIPTION).toBe(
      "Extract 2D/3D pose keypoints from video libraries with MMPose, stored on Backblaze B2"
    );
  });
});
