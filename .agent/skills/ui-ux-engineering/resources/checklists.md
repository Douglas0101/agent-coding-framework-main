# UI/UX Engineering Resources

## Quick Reference Checklists

### Pre-Development Checklist
- [ ] Reviewed design specifications
- [ ] Identified required design tokens
- [ ] Planned component structure
- [ ] Considered accessibility requirements
- [ ] Identified reusable patterns

### Component Development Checklist
- [ ] Uses TypeScript with proper types
- [ ] Uses CSS variables (no hardcoded colors)
- [ ] Has proper ARIA labels
- [ ] Keyboard accessible
- [ ] Has visible focus states
- [ ] Loading states implemented
- [ ] Error states implemented
- [ ] Empty states implemented
- [ ] Responsive on all breakpoints
- [ ] Uses semantic HTML

### Accessibility Checklist
- [ ] Screen reader tested
- [ ] Keyboard-only navigation works
- [ ] Focus order is logical
- [ ] Color is not sole indicator
- [ ] Contrast ratios meet AA
- [ ] Motion respects prefers-reduced-motion
- [ ] Form fields have labels
- [ ] Error messages are accessible

### Performance Checklist
- [ ] No unnecessary re-renders
- [ ] Images optimized with Next/Image
- [ ] Heavy components code-split
- [ ] Large lists virtualized
- [ ] CSS animations use transform/opacity
- [ ] Third-party imports tree-shaken

---

## Medical Imaging UI Specifics

### DICOM Viewer Requirements
1. **Window/Level Controls**
   - Preset buttons (Bone, Soft Tissue, Lung, etc.)
   - Manual adjustment sliders
   - Real-time feedback

2. **Navigation**
   - Slice scroll (mouse wheel)
   - Series thumbnails
   - Study navigation

3. **Measurement Tools**
   - Ruler/Distance
   - Angle
   - ROI (Region of Interest)
   - Annotation text

4. **Display Options**
   - Zoom (pinch/scroll)
   - Pan (drag)
   - Rotate/Flip
   - Invert

### Clinical Color Coding
| Finding | Color | Token |
|---------|-------|-------|
| Critical/Positive | Red | `--accent-red` |
| Uncertain/Pending | Amber | `--accent-amber` |
| Normal/Negative | Teal | `--accent-teal` |
| Calibrated/Verified | Teal | `--accent-teal` |

### Heatmap Intensity Mapping
```
Score 0.0-0.3: Low intensity  → heatmap-low (green)
Score 0.3-0.6: Mid intensity  → heatmap-mid (amber)
Score 0.6-1.0: High intensity → heatmap-high (red)
```

---

## Keyboard Shortcuts Reference

### Global
| Key | Action |
|-----|--------|
| `Esc` | Close modal/panel |
| `?` | Show keyboard shortcuts |
| `Ctrl+S` | Save/Export |
| `/` | Focus search |

### Viewer
| Key | Action |
|-----|--------|
| `↑/↓` | Previous/Next slice |
| `+/-` | Zoom in/out |
| `R` | Reset view |
| `H` | Toggle heatmap |
| `1-9` | Jump to prediction N |
| `Space` | Play/Pause cine |

---

## Responsive Breakpoints

```css
/* Tailwind v4 defaults */
sm: 40rem   /* 640px */
md: 48rem   /* 768px */
lg: 64rem   /* 1024px */
xl: 80rem   /* 1280px */
2xl: 96rem  /* 1536px */
```

### Medical Layout Patterns
- **Mobile**: Single column, stacked panels
- **Tablet**: Sidebar collapsed, viewer full width
- **Desktop**: Sidebar 220px + Viewer + Panel 320px
- **Wide**: Multi-series side-by-side view

---

## Animation Timing Guidelines

| Animation | Duration | Easing |
|-----------|----------|--------|
| Micro (hover) | 150-200ms | ease-out |
| Small (button) | 200-300ms | ease-out |
| Medium (modal) | 300-400ms | ease-out |
| Large (page) | 400-500ms | ease-in-out |
| Loading pulse | 2-3s | ease-in-out |

### Heatmap Pulse Animations
```css
/* High urgency - fast pulse */
@keyframes heatPulseHigh { 1.4s ease-in-out infinite }

/* Medium urgency */
@keyframes heatPulseMid { 2.0s ease-in-out infinite }

/* Low urgency - slow pulse */
@keyframes heatPulseLow { 2.8s ease-in-out infinite }
```

---

## Testing Checklist

### Visual Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Chrome
- [ ] Mobile Safari

### Accessibility Testing Tools
1. **Automated**:
   - axe DevTools extension
   - Lighthouse accessibility audit
   - eslint-plugin-jsx-a11y

2. **Manual**:
   - VoiceOver (macOS/iOS)
   - NVDA (Windows)
   - Keyboard-only navigation

### Component Testing
```tsx
// Jest + Testing Library example
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("Button", () => {
  it("should be keyboard accessible", async () => {
    const onClick = jest.fn();
    render(<Button onClick={onClick}>Click me</Button>);

    const button = screen.getByRole("button");
    button.focus();
    await userEvent.keyboard("{Enter}");

    expect(onClick).toHaveBeenCalled();
  });
});
```

---

## Useful Links

### Design
- [Figma Medical UI Kit](https://www.figma.com/)
- [DICOM Standard](https://www.dicomstandard.org/)
- [Material Design 3](https://m3.material.io/)

### Accessibility
- [WCAG 2.2 Guidelines](https://www.w3.org/WAI/WCAG22/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

### Performance
- [web.dev Performance](https://web.dev/performance/)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [React Profiler](https://react.dev/reference/react/Profiler)

### Component Libraries (Reference)
- [Radix UI](https://www.radix-ui.com/)
- [Headless UI](https://headlessui.com/)
- [shadcn/ui](https://ui.shadcn.com/)
