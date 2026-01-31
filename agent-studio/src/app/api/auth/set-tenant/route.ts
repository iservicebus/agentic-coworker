import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { getToken } from "next-auth/jwt";
import { validateTenantExists } from "@/lib/tenant";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { tenant } = body;

    if (!tenant || typeof tenant !== "string") {
      return NextResponse.json(
        { error: "Invalid tenant name" },
        { status: 400 }
      );
    }

    // Validate that the tenant exists in the database
    const tenantExists = await validateTenantExists(tenant);
    if (!tenantExists) {
      return NextResponse.json(
        { error: "Tenant does not exist" },
        { status: 404 }
      );
    }

    console.log("Setting tenant in cookie:", tenant);

    // Store tenant in a cookie that will be read by the client
    const response = NextResponse.json({ 
      success: true, 
      tenant,
      message: "Tenant set successfully. Please refresh the session." 
    });

    // Store tenant in a cookie (httpOnly: false so JavaScript can read it)
    response.cookies.set("tenant", tenant, {
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 30, // 30 days
      path: "/",
    });

    return response;
  } catch (error) {
    console.error("Error setting tenant:", error);
    return NextResponse.json(
      { error: "Failed to set tenant" },
      { status: 500 }
    );
  }
}
