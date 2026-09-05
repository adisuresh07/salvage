import type { SimulatorRun } from "./api/client";

interface Checkout {
  open(): void;
  on(event: "payment.failed", callback: () => void): void;
}
declare global {
  interface Window { Razorpay?: new (options: Record<string, unknown>) => Checkout; }
}

let loading: Promise<void> | null = null;

export async function openTestCheckout(run: SimulatorRun, onUpdate: (message: string) => void) {
  if (!run.checkout_key_id?.startsWith("rzp_test_") || !run.order_id) {
    throw new Error("A confirmed Test Mode order is required.");
  }
  if (!window.Razorpay) {
    loading ??= new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => { script.remove(); loading = null; reject(new Error("Razorpay Checkout could not load. Check your connection and try again.")); };
      document.head.appendChild(script);
    });
    await loading;
  }
  if (!window.Razorpay) throw new Error("Razorpay Checkout is unavailable in this browser.");
  const checkout = new window.Razorpay({
    key: run.checkout_key_id, order_id: run.order_id, amount: run.amount_minor,
    currency: "INR", name: "Salvage Sandbox", description: "Test payment — no real money",
    prefill: { name: "Salvage Test", email: "demo@example.com" },
    theme: { color: "#193c35" },
    handler: () => onUpdate("Checkout reported success. Use Check Razorpay status for server-side confirmation."),
    modal: { ondismiss: () => onUpdate("Checkout closed. Check Razorpay status to see whether a test payment was recorded.") },
  });
  checkout.on("payment.failed", () => onUpdate("Checkout reported a failure. Waiting for a signed webhook; you can also Check Razorpay status."));
  checkout.open();
}
