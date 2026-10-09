import { NextResponse } from "next/server";

// In-memory global store for the serverless instance
let cachedState = null;
let lastUpdate = 0;

export async function POST(request) {
  try {
    const authHeader = request.headers.get("authorization");
    const secret = process.env.APEX_API_SECRET;
    
    // If secret configured, verify bearer token
    if (secret && authHeader !== `Bearer ${secret}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const payload = await request.json();
    cachedState = {
      ...payload,
      received_at: new Date().toISOString(),
    };
    lastUpdate = Date.now();

    return NextResponse.json({
      success: true,
      timestamp: lastUpdate,
      status: "STORED",
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
}

export async function GET() {
  if (!cachedState) {
    return NextResponse.json({
      status: "WAITING_FOR_DATA",
      message: "No live telemetry pushed from cloud bot yet.",
    });
  }
  return NextResponse.json(cachedState);
}
