import { notFound } from "next/navigation";

// Unknown /v2 paths render the v2 not-found screen instead of the root one.
export default function UnknownV2Route() {
  notFound();
}
