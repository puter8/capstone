import { notFound } from "next/navigation";

// Unknown paths render the shared not-found screen; static API/dev routes win.
export default function UnknownV2Route() {
  notFound();
}
