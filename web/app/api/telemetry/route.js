import { NextResponse } from "next/server";
import { setLatestState, getLatestState } from "../store";

export async function POST(request) {
  try {
    const authHeader = request.headers.get("authorization");
    const secret = process.env.APEX_API_SECRET;
    
    // If secret configured, verify bearer token
    if (secret && authHeader !== `Bearer ${secret}`) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const payload = await request.json();
    setLatestState(payload);

    return NextResponse.json({
      success: true,
      timestamp: Date.now(),
      status: "STORED",
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
}

export async function GET() {
  const state = getLatestState();
  if (!state) {
    return NextResponse.json({
      status: "WAITING_FOR_DATA",
      message: "No live telemetry pushed from cloud bot yet.",
    });
  }
  return NextResponse.json(state);
}
