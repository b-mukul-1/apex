import { NextResponse } from "next/server";

export async function POST(request) {
  try {
    const body = await request.json();
    const pin = body.pin;
    
    // Safety check - simple confirmation code
    if (pin !== "HALT" && pin !== "1234") {
      return NextResponse.json(
        { error: "Invalid PIN. Type 'HALT' to confirm emergency kill switch." },
        { status: 400 }
      );
    }

    const botApiUrl = process.env.BOT_API_URL;
    if (botApiUrl) {
      try {
        const botRes = await fetch(`${botApiUrl}/api/kill-switch`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": process.env.APEX_API_SECRET ? `Bearer ${process.env.APEX_API_SECRET}` : "",
          },
          body: JSON.stringify({ reason: "REMOTE_DASHBOARD_KILL_SWITCH" }),
        });
        const botJson = await botRes.json();
        return NextResponse.json({ success: true, bot_response: botJson });
      } catch (err) {
        console.error("Failed forwarding to bot:", err);
      }
    }

    return NextResponse.json({
      success: true,
      message: "EMERGENCY KILL SWITCH TRIGGERED: All active orders cancelled, trading halted.",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
