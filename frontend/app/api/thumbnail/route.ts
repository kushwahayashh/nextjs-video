import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import { join } from "path";

const execAsync = promisify(exec);

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const fileName: string | undefined = body?.fileName;

    if (!fileName || typeof fileName !== "string") {
      return NextResponse.json({ error: "Missing or invalid fileName" }, { status: 400 });
    }

    const videosDir = join(process.cwd(), '..', 'videos');
    const thumbnailsDir = join(process.cwd(), 'public', 'thumbnails');
    const videoPath = join(videosDir, fileName);
    const scriptPath = join(process.cwd(), '..', 'backend', 'videoprocessing', 'generate_sprite.py');

    const command = [
      "python3",
      scriptPath,
      "--input", `"${videoPath}"`,
      "--outdir", `"${thumbnailsDir}"`,
      "--mode", "thumbnail",
      "--image-format", "jpeg",
    ].join(" ");

    const { stderr } = await execAsync(command);

    if (stderr) {
      console.error(`[thumbnail] Error generating thumbnail for ${fileName}:`, stderr);
      return NextResponse.json({ error: "Failed to generate thumbnail" }, { status: 500 });
    }

    const thumbnailFile = `${fileName.split('.')[0]}.jpeg`;
    const thumbnailUrl = `/thumbnails/${thumbnailFile}`;

    return NextResponse.json({ ok: true, thumbnailUrl });
  } catch (error) {
    console.error("[thumbnail] Internal error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}


