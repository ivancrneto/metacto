/// <reference types="vite/client" />

// The View Transitions API is used to animate list reordering; some @types/react
// versions don't yet include this CSS property.
import "react";
declare module "react" {
  interface CSSProperties {
    viewTransitionName?: string;
  }
}
