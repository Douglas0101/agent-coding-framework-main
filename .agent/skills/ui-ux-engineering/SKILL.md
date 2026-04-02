---
name: ui-ux-engineering
description: Advanced skill for professional UI/UX analysis, improvements, and implementation
  of enterprise-grade interface patterns for medical imaging applications.
---

# UI/UX Engineering Skill

## Overview

This skill provides comprehensive guidelines and tools for analyzing, improving, and implementing professional-grade user interfaces for the Vitruviano Clinical AI Viewer. It covers React 19 Server Components, Next.js 16 App Router, TailwindCSS v4, accessibility compliance, and performance optimization.

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Design System Standards](#2-design-system-standards)
3. [React 19 Patterns](#3-react-19-patterns)
4. [Next.js 16 App Router](#4-nextjs-16-app-router)
5. [TailwindCSS v4 Patterns](#5-tailwindcss-v4-patterns)
6. [Component Architecture](#6-component-architecture)
7. [State Management](#7-state-management)
8. [Accessibility Guidelines](#8-accessibility-guidelines)
9. [Performance Optimization](#9-performance-optimization)
10. [API Integration](#10-api-integration)
11. [Quality Checklist](#11-quality-checklist)
12. [Quick Reference](#12-quick-reference)

---

## 1. Technology Stack

### 1.1 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Next.js | 16.1.3 | React framework with App Router |
| React | 19.2.3 | UI library with Server Components |
| TailwindCSS | 4.x | Utility-first CSS framework |
| TypeScript | 5.x | Type safety |

### 1.2 Recommended Additions

```json
{
  "dependencies": {
    "zustand": "^5.0.0",
    "swr": "^2.3.0",
    "clsx": "^2.1.0"
  },
  "devDependencies": {
    "@types/node": "^22",
    "@types/react": "^19",
    "eslint": "^9",
    "eslint-config-next": "16.1.3"
  }
}
```

---

## 2. Design System Standards

### 2.1 Color Tokens (theme.css)

```css
:root {
  /* Surfaces (Dark Neutral) */
  --surface-0: #09090b;
  --surface-1: #121215;
  --surface-2: #1c1c20;
  --surface-3: #27272a;
  --surface-glass: rgba(9, 9, 11, 0.9);

  /* Text */
  --text-primary: #f4f4f5;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;

  /* Accents */
  --accent-teal: #31c6b2;    /* Success, active, calibrated */
  --accent-blue: #3b82f6;    /* Actions, links */
  --accent-amber: #f59e0b;   /* Warning, pending */
  --accent-red: #ef4444;     /* Error, critical findings */
  --accent-lilac: #a78bfa;   /* Info, metadata */

  /* Heatmap Gradient */
  --heatmap-low: #2fb2a0;
  --heatmap-mid: #e6b84a;
  --heatmap-high: #ef4444;
}
```

### 2.2 Semantic Color Usage

| Semantic | Token | Use Case |
|----------|-------|----------|
| Success | `--accent-teal` | Calibrated, active, positive |
| Warning | `--accent-amber` | Uncertain, pending, attention |
| Error | `--accent-red` | Critical findings, alerts |
| Info | `--accent-lilac` | Metadata, secondary info |
| Action | `--accent-blue` | Buttons, links, interactive |

### 2.3 Typography Scale

```tsx
// Headings
className="text-3xl font-semibold leading-tight"     // h1
className="text-2xl font-semibold"                   // h2
className="text-lg font-semibold"                    // h3
className="text-sm font-medium"                      // h4

// Body
className="text-[15px] leading-7 text-(--text-secondary)"  // Paragraph
className="text-sm text-(--text-secondary)"                // Body small

// Labels
className="text-xs uppercase tracking-[0.2em] text-(--text-muted)"  // Section
className="text-[11px] text-(--text-muted)"                          // Caption
```

### 2.4 Spacing Standards

| Context | Padding | Gap |
|---------|---------|-----|
| Cards | `p-5` to `p-8` | - |
| Sections | `py-6` | `gap-6` |
| Items | `py-3 px-4` | `gap-3` |
| Compact | `py-2 px-3` | `gap-2` |

### 2.5 Border Radius

```tsx
// Large containers (cards, panels)
className="rounded-lg"       // --radius-lg: 18px

// Inner elements (buttons, inputs)
className="rounded-md"       // --radius-md: 14px

// Pills, badges
className="rounded-full"     // Circular
```

---

## 3. React 19 Patterns

### 3.1 Server Components (Default)

```tsx
// app/studies/page.tsx - Server Component by default
import { getStudies } from "@/lib/api";

export default async function StudiesPage() {
  // Direct database/API access (no useState/useEffect)
  const studies = await getStudies();

  return (
    <div className="grid gap-4">
      {studies.map((study) => (
        <StudyCard key={study.id} study={study} />
      ))}
    </div>
  );
}
```

### 3.2 Client Components

```tsx
// components/viewer/ImageViewer.tsx
"use client";  // Required for client-side interactivity

import { useState, useCallback } from "react";

interface ImageViewerProps {
  imageUrl: string;
  annotations: Annotation[];
}

export default function ImageViewer({ imageUrl, annotations }: ImageViewerProps) {
  const [zoom, setZoom] = useState(100);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const handleZoom = useCallback((delta: number) => {
    setZoom((prev) => Math.max(50, Math.min(200, prev + delta)));
  }, []);

  return (
    <div className="relative bg-black">
      {/* Canvas with zoom transform */}
      {/* Annotation overlays */}
    </div>
  );
}
```

### 3.3 use() Hook for Suspense

```tsx
"use client";
import { use } from "react";

function PredictionResults({ promise }: { promise: Promise<Prediction[]> }) {
  // Suspense-compatible data fetching
  const predictions = use(promise);

  return (
    <ul>
      {predictions.map((pred) => (
        <li key={pred.className}>{pred.className}: {pred.score}</li>
      ))}
    </ul>
  );
}

// Usage with Suspense boundary
export default function PredictionPanel() {
  const predictionsPromise = fetchPredictions();

  return (
    <Suspense fallback={<Skeleton />}>
      <PredictionResults promise={predictionsPromise} />
    </Suspense>
  );
}
```

### 3.4 useOptimistic for Optimistic Updates

```tsx
"use client";
import { useOptimistic, useTransition } from "react";

function AnnotationList({ annotations }: { annotations: Annotation[] }) {
  const [isPending, startTransition] = useTransition();
  const [optimisticAnnotations, addOptimistic] = useOptimistic(
    annotations,
    (state, newAnnotation: Annotation) => [...state, newAnnotation]
  );

  async function handleAdd(formData: FormData) {
    const newAnnotation = parseFormData(formData);

    // Immediately show optimistic update
    startTransition(() => {
      addOptimistic(newAnnotation);
    });

    // Then persist to server
    await createAnnotation(newAnnotation);
  }

  return (
    <form action={handleAdd}>
      {/* Form fields */}
    </form>
  );
}
```

### 3.5 useActionState for Form Actions

```tsx
"use client";
import { useActionState } from "react";

async function submitFeedback(prevState: FormState, formData: FormData) {
  const feedback = formData.get("feedback") as string;

  try {
    await fetch("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ feedback }),
    });
    return { success: true, message: "Feedback submitted" };
  } catch {
    return { success: false, message: "Failed to submit" };
  }
}

function FeedbackForm() {
  const [state, action, isPending] = useActionState(submitFeedback, {
    success: false,
    message: "",
  });

  return (
    <form action={action}>
      <textarea name="feedback" required />
      <button type="submit" disabled={isPending}>
        {isPending ? "Submitting..." : "Submit"}
      </button>
      {state.message && <p>{state.message}</p>}
    </form>
  );
}
```

---

## 4. Next.js 16 App Router

### 4.1 Directory Structure

```
frontend/src/
├── app/
│   ├── layout.tsx          # Root layout (Server)
│   ├── page.tsx             # Home page
│   ├── globals.css          # Global styles
│   ├── loading.tsx          # Loading UI (Suspense)
│   ├── error.tsx            # Error boundary
│   ├── not-found.tsx        # 404 page
│   ├── studies/
│   │   ├── page.tsx         # /studies
│   │   └── [id]/
│   │       ├── page.tsx     # /studies/:id
│   │       └── loading.tsx  # Study loading
│   └── api/
│       └── predict/
│           └── route.ts     # API Route
├── components/
│   ├── common/              # Shared primitives
│   ├── layout/              # App structure
│   └── viewer/              # Medical viewer
├── lib/
│   ├── api.ts               # API client
│   └── utils.ts             # Utilities
└── types/
    └── index.ts             # TypeScript types
```

### 4.2 Root Layout

```tsx
// app/layout.tsx
import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const sansFont = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Vitruviano Clinical Viewer",
  description: "AI-powered chest X-ray analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${sansFont.variable} ${monoFont.variable}`}>
      <body className="bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
```

### 4.3 Loading UI (Suspense)

```tsx
// app/studies/loading.tsx
import { Skeleton } from "@/components/common";

export default function StudiesLoading() {
  return (
    <div className="grid gap-4 p-6">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-24 w-full rounded-lg" />
      ))}
    </div>
  );
}
```

### 4.4 Error Boundary

```tsx
// app/studies/error.tsx
"use client";

import { useEffect } from "react";
import { Button } from "@/components/common";

export default function StudiesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Studies error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8">
      <h2 className="text-xl font-semibold text-(--accent-red)">
        Something went wrong
      </h2>
      <p className="text-(--text-secondary)">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

### 4.5 API Routes

```tsx
// app/api/predict/route.ts
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const file = formData.get("file") as File;

  if (!file) {
    return NextResponse.json(
      { error: "No file provided" },
      { status: 400 }
    );
  }

  // Proxy to backend
  const backendFormData = new FormData();
  backendFormData.append("file", file);

  const response = await fetch(`${BACKEND_URL}/predict`, {
    method: "POST",
    body: backendFormData,
  });

  const data = await response.json();
  return NextResponse.json(data);
}
```

### 4.6 Server Actions

```tsx
// app/actions/predictions.ts
"use server";

import { revalidatePath } from "next/cache";

export async function runInference(formData: FormData) {
  const imageId = formData.get("imageId") as string;

  const response = await fetch(`${process.env.BACKEND_URL}/inference/demo`, {
    method: "POST",
    body: JSON.stringify({ image_id: imageId }),
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error("Inference failed");
  }

  const result = await response.json();

  // Revalidate the predictions cache
  revalidatePath("/viewer");

  return result;
}
```

---

## 5. TailwindCSS v4 Patterns

### 5.1 Modern JIT Syntax

```tsx
// TailwindCSS v4 uses simplified syntax for CSS variables

// ✅ Correct - Modern v4 syntax
className="text-(--text-secondary)"
className="bg-(--surface-1)"
className="border-(--border-soft)"

// ❌ Old - Avoid bracket notation with var()
className="text-[var(--text-secondary)]"
className="bg-[var(--surface-0)]"
```

### 5.2 Semantic Utility Classes

```tsx
// ✅ Use semantic class names from @theme inline
className="text-foreground"      // --color-foreground
className="bg-background"        // --color-background

// ✅ Standard Tailwind utilities
className="rounded-lg"           // Not rounded-[var(--radius-lg)]
className="rounded-md"           // Not rounded-[var(--radius-md)]
className="shrink-0"             // Not flex-shrink-0
```

### 5.3 Animation Utilities

```tsx
// Use Tailwind's built-in animation classes
className="animate-pulse"
className="animate-spin"

// Custom animations defined in globals.css
className="animate-[shimmer_2s_infinite]"
className="animate-[slideInRight_0.3s_ease-out]"
className="animate-[fadeIn_0.2s_ease-out]"
```

### 5.4 Responsive Design

```tsx
// Mobile-first responsive design
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
className="p-4 md:p-6 lg:p-8"
className="text-sm md:text-base"
className="hidden lg:block"
```

### 5.5 Dark Mode

```tsx
// The project uses a dark-only theme
// All components are designed for dark backgrounds

// If light mode is needed in future:
className="bg-surface-0 dark:bg-surface-0"
className="text-foreground dark:text-foreground"
```

---

## 6. Component Architecture

### 6.1 File Structure

```
src/components/
├── common/                # Shared primitives
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Modal.tsx
│   ├── Toast.tsx
│   ├── Skeleton.tsx
│   ├── Tooltip.tsx
│   └── index.ts
├── layout/                # App structure
│   ├── AppShell.tsx
│   ├── Sidebar.tsx
│   ├── Topbar.tsx
│   └── index.ts
├── viewer/                # Medical viewer
│   ├── ImageViewer.tsx
│   ├── HeatmapOverlay.tsx
│   ├── PredictionPanel.tsx
│   ├── SliceTimeline.tsx
│   ├── BoundingBoxOverlay.tsx
│   └── index.ts
└── study/                 # Study management
    ├── StudyCard.tsx
    ├── StudyList.tsx
    └── index.ts
```

### 6.2 Component Template

```tsx
/**
 * @component Button
 * @description Primary action button with variants
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { clsx } from "clsx";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant */
  variant?: "primary" | "secondary" | "ghost" | "danger";
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Loading state */
  isLoading?: boolean;
  /** Icon before text */
  leftIcon?: ReactNode;
  /** Children elements */
  children: ReactNode;
}

const variantStyles = {
  primary: "bg-(--accent-teal) text-[#06151a] hover:brightness-110",
  secondary: "bg-(--surface-2) text-foreground hover:bg-(--surface-3)",
  ghost: "bg-transparent text-(--text-secondary) hover:bg-(--surface-2)",
  danger: "bg-(--accent-red) text-white hover:brightness-110",
} as const;

const sizeStyles = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
} as const;

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      children,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={clsx(
          "inline-flex items-center justify-center gap-2",
          "rounded-md font-medium",
          "transition-(--transition-fast)",
          "focus-visible:outline-2 focus-visible:outline-(--accent-teal)",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <span className="animate-spin">⏳</span>
        ) : (
          leftIcon
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export default Button;
```

### 6.3 Compound Component Pattern

```tsx
// components/viewer/Viewer.tsx
import ViewerRoot from "./ViewerRoot";
import ViewerToolbar from "./ViewerToolbar";
import ViewerCanvas from "./ViewerCanvas";
import ViewerOverlay from "./ViewerOverlay";

export const Viewer = {
  Root: ViewerRoot,
  Toolbar: ViewerToolbar,
  Canvas: ViewerCanvas,
  Overlay: ViewerOverlay,
} as const;

// Usage
<Viewer.Root studyId="ST-90214">
  <Viewer.Toolbar />
  <Viewer.Canvas>
    <Viewer.Overlay type="heatmap" />
    <Viewer.Overlay type="bounding-box" />
  </Viewer.Canvas>
</Viewer.Root>
```

---

## 7. State Management

### 7.1 Zustand Store

```tsx
// store/viewer.ts
import { create } from "zustand";

interface ViewerState {
  currentSlice: number;
  zoom: number;
  activeLayers: string[];
  hoveredPredictionId: string | null;

  setSlice: (slice: number) => void;
  setZoom: (zoom: number) => void;
  toggleLayer: (layer: string) => void;
  setHoveredPrediction: (id: string | null) => void;
}

export const useViewerStore = create<ViewerState>((set) => ({
  currentSlice: 1,
  zoom: 100,
  activeLayers: ["image", "predictions"],
  hoveredPredictionId: null,

  setSlice: (slice) => set({ currentSlice: slice }),

  setZoom: (zoom) => set({ zoom: Math.max(50, Math.min(200, zoom)) }),

  toggleLayer: (layer) =>
    set((state) => ({
      activeLayers: state.activeLayers.includes(layer)
        ? state.activeLayers.filter((l) => l !== layer)
        : [...state.activeLayers, layer],
    })),

  setHoveredPrediction: (id) => set({ hoveredPredictionId: id }),
}));
```

### 7.2 Using Store in Components

```tsx
"use client";
import { useViewerStore } from "@/store/viewer";

function PredictionPanel() {
  const { hoveredPredictionId, setHoveredPrediction } = useViewerStore();

  return (
    <ul>
      {predictions.map((pred) => (
        <li
          key={pred.id}
          onMouseEnter={() => setHoveredPrediction(pred.id)}
          onMouseLeave={() => setHoveredPrediction(null)}
          className={clsx(
            "p-3 rounded-md transition-(--transition-fast)",
            hoveredPredictionId === pred.id && "bg-(--surface-2)"
          )}
        >
          {pred.className}
        </li>
      ))}
    </ul>
  );
}
```

### 7.3 SWR for Data Fetching

```tsx
// hooks/useStudy.ts
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useStudy(studyId: string) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/studies/${studyId}`,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  return {
    study: data,
    isLoading,
    isError: error,
    refresh: mutate,
  };
}

export function usePredictions(imageId: string) {
  const { data, error, isLoading } = useSWR(
    imageId ? `/api/predictions/${imageId}` : null,
    fetcher
  );

  return {
    predictions: data?.predictions ?? [],
    metadata: data?.metadata,
    isLoading,
    isError: error,
  };
}
```

---

## 8. Accessibility Guidelines

### 8.1 WCAG 2.2 AA Compliance Checklist

- [ ] All interactive elements are keyboard accessible
- [ ] Focus is visible and follows logical order
- [ ] Color is not the only means of conveying information
- [ ] Text has minimum 4.5:1 contrast ratio
- [ ] Non-text elements have 3:1 contrast ratio
- [ ] All images have alt text
- [ ] Form inputs have associated labels
- [ ] Error messages are clear and accessible
- [ ] Motion can be disabled (prefers-reduced-motion)

### 8.2 Focus Styles

```css
/* theme.css */
:focus-visible {
  outline: 2px solid var(--accent-teal);
  outline-offset: 2px;
}

:focus:not(:focus-visible) {
  outline: none;
}
```

```tsx
// Tailwind classes
className="focus-visible:outline-2 focus-visible:outline-(--accent-teal) focus-visible:outline-offset-2"
```

### 8.3 ARIA Labels

```tsx
// ✅ Icon button with label
<button
  aria-label="Export study as DICOM format"
  className="p-2 rounded-md hover:bg-(--surface-2)"
>
  <ExportIcon aria-hidden="true" />
</button>

// ✅ Live region for dynamic content
<div
  role="status"
  aria-live="polite"
  aria-atomic="true"
>
  {statusMessage}
</div>

// ✅ Accessible modal
<dialog
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
>
  <h2 id="modal-title">Confirm Action</h2>
  <p id="modal-description">Are you sure?</p>
</dialog>
```

### 8.4 Reduced Motion

```css
/* theme.css */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 9. Performance Optimization

### 9.1 Image Optimization

```tsx
import Image from "next/image";

// ✅ Use Next.js Image for automatic optimization
<Image
  src={dicomThumbnail}
  alt="CT scan thumbnail"
  width={256}
  height={256}
  placeholder="blur"
  blurDataURL={blurPlaceholder}
  loading="lazy"
/>

// For medical images that need precise rendering
<Image
  src={xrayImage}
  alt="Chest X-ray"
  fill
  sizes="(max-width: 768px) 100vw, 50vw"
  quality={100}
  priority  // Above the fold
/>
```

### 9.2 Component Memoization

```tsx
import { memo, useMemo, useCallback } from "react";

// Memoize expensive components
const PredictionList = memo(function PredictionList({
  predictions
}: Props) {
  return predictions.map((pred) => (
    <PredictionItem key={pred.id} {...pred} />
  ));
});

// Memoize expensive calculations
const sortedPredictions = useMemo(
  () => predictions.sort((a, b) => b.score - a.score),
  [predictions]
);

// Memoize callbacks
const handleSelect = useCallback((id: string) => {
  onSelect(id);
}, [onSelect]);
```

### 9.3 Code Splitting

```tsx
import dynamic from "next/dynamic";

// Lazy load heavy components
const HeatmapViewer = dynamic(
  () => import("@/components/viewer/HeatmapViewer"),
  {
    loading: () => <Skeleton className="h-64 w-full" />,
    ssr: false,  // Client-only for canvas rendering
  }
);

const DicomViewer = dynamic(
  () => import("@/components/viewer/DicomViewer"),
  {
    ssr: false,
  }
);
```

### 9.4 Bundle Analysis

```bash
# Analyze bundle size
npm run build -- --analyze

# Or use @next/bundle-analyzer
ANALYZE=true npm run build
```

---

## 10. API Integration

### 10.1 API Client

```tsx
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestOptions extends RequestInit {
  timeout?: number;
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...fetchOptions,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  // Dataset endpoints
  listImages: (params?: { finding?: string; limit?: number }) =>
    apiRequest<{ images: ImageMeta[]; total: number }>(
      `/dataset/images?${new URLSearchParams(params as Record<string, string>)}`
    ),

  getImage: (imageId: string) =>
    apiRequest<Blob>(`/dataset/images/${imageId}`),

  // Inference endpoints
  runInference: (imageId: string) =>
    apiRequest<InferenceResult>(`/inference/demo?image_id=${imageId}`, {
      method: "POST",
    }),

  // Health
  healthCheck: () =>
    apiRequest<{ status: string }>("/health"),
};
```

### 10.2 Type Definitions

```tsx
// types/index.ts
export interface Prediction {
  className: string;
  score: number;
  isDetected: boolean;
  threshold: number;
}

export interface InferenceResult {
  imageId: string;
  imageUrl: string;
  predictions: Prediction[];
  metadata: {
    processingTimeMs: number;
    temperature: number;
    ece: number;
    mce: number;
  };
  groundTruth?: BoundingBox[];
}

export interface BoundingBox {
  findingLabel: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ImageMeta {
  imageId: string;
  findingLabels: string[];
  patientAge: number;
  patientGender: string;
  viewPosition: string;
  width: number;
  height: number;
  hasAnnotations: boolean;
}
```

---

## 11. Quality Checklist

### Pre-Commit Checklist

- [ ] **Visual**: Component matches design specification
- [ ] **Responsive**: Works on mobile, tablet, and desktop
- [ ] **Dark Theme**: All colors use CSS variables
- [ ] **Keyboard**: All interactions work with keyboard
- [ ] **Focus**: Focus states are visible and logical
- [ ] **ARIA**: Screen reader can understand the content
- [ ] **Loading**: Loading states are implemented
- [ ] **Error**: Error states are handled gracefully
- [ ] **Empty**: Empty states provide guidance
- [ ] **Performance**: No unnecessary re-renders
- [ ] **Types**: All props are properly typed
- [ ] **Tests**: Component has unit/integration tests

### Review Checklist

- [ ] Consistent with existing design system
- [ ] No magic numbers (use tokens)
- [ ] Semantic HTML elements used
- [ ] No hardcoded strings (i18n-ready)
- [ ] Browser DevTools shows no console errors
- [ ] Lighthouse accessibility score ≥ 90
- [ ] Bundle size impact is acceptable

---

## 12. Quick Reference

### 12.1 Quick Reference Card

```
╔══════════════════════════════════════════════════════════════╗
║                   VITRUVIANO UI/UX QUICK REF                 ║
╠══════════════════════════════════════════════════════════════╣
║ COLORS                                                       ║
║ ├─ Success:  var(--accent-teal)   #31c6b2                   ║
║ ├─ Warning:  var(--accent-amber)  #f59e0b                   ║
║ ├─ Error:    var(--accent-red)    #ef4444                   ║
║ ├─ Action:   var(--accent-blue)   #3b82f6                   ║
║ └─ Surfaces: surface-0 → surface-3 (dark to lighter)        ║
╠══════════════════════════════════════════════════════════════╣
║ TAILWIND v4 SYNTAX                                           ║
║ ├─ Variables:  text-(--text-secondary)                      ║
║ ├─ Semantic:   bg-background, text-foreground               ║
║ ├─ Radius:     rounded-lg, rounded-md                       ║
║ └─ Shrink:     shrink-0 (not flex-shrink-0)                 ║
╠══════════════════════════════════════════════════════════════╣
║ REACT 19 PATTERNS                                            ║
║ ├─ Server Components: Default (no "use client")             ║
║ ├─ Client Components: Add "use client" directive            ║
║ ├─ use() hook:        Suspense-compatible promises          ║
║ └─ useActionState:    Form actions with state               ║
╠══════════════════════════════════════════════════════════════╣
║ NEXT.JS 16 APP ROUTER                                        ║
║ ├─ layout.tsx:  Shared UI (Server)                          ║
║ ├─ page.tsx:    Route content                               ║
║ ├─ loading.tsx: Suspense fallback                           ║
║ └─ error.tsx:   Error boundary                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

*Last Updated: 2026-01-19 | Version: 2.0.0*
