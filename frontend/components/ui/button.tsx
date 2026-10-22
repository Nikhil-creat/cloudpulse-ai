import { cva, type VariantProps } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import * as React from "react";

const button = cva("inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-medium transition disabled:opacity-50", {
  variants: { variant: {
    solid: "bg-gradient-to-b from-white to-neutral-300 text-neutral-900 hover:shadow-[0_0_22px_rgba(186,208,255,0.35)]",
    ghost: "border border-white/30 bg-white/5 text-white hover:bg-white/10",
    danger: "border border-red-400/50 text-red-300 hover:bg-red-500/10" } },
  defaultVariants: { variant: "solid" } });

export function Button({ className, variant, ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof button>) {
  return <button className={twMerge(clsx(button({ variant }), className))} {...p} />;
}
