# 🎨 TalkSense AI - Animation & Interaction Guide

## Quick Reference for Developers

This guide provides a quick reference for all custom animations and micro-interactions implemented in the TalkSense AI frontend.

---

## 📚 Custom Animation Classes

### Fade Animations

```jsx
// Fade in from opacity 0 to 1
<div className="animate-fade-in">
  Content fades in smoothly
</div>
```

**Duration**: 300ms  
**Easing**: ease-in-out  
**Use Case**: Page loads, modal appearances

---

### Slide Animations

```jsx
// Slide up from bottom
<div className="animate-slide-up">
  Content slides up from 20px below
</div>

// Slide down from top
<div className="animate-slide-down">
  Content slides down from 10px above
</div>
```

**Duration**: 400ms (slide-up), 300ms (slide-down)  
**Easing**: ease-out  
**Use Case**: Card entries, list items, error messages

---

### Scale Animations

```jsx
// Scale in from 95% to 100%
<div className="animate-scale-in">
  Content scales in smoothly
</div>

// Scale on hover
<button className="hover-scale">
  Scales to 105% on hover
</button>

// Scale on click
<button className="active:scale-95">
  Scales to 95% when clicked
</button>
```

**Duration**: 200ms  
**Easing**: ease-out  
**Use Case**: Success states, button feedback, interactive elements

---

### Loading Animations

```jsx
// Shimmer effect for loading states
<div className="animate-shimmer h-4 rounded">
  Loading shimmer effect
</div>

// Subtle pulse
<div className="animate-pulse-subtle">
  Gently pulses opacity
</div>
```

**Duration**: 2s (infinite)  
**Use Case**: Loading indicators, skeleton screens

---

### Transition Utilities

```jsx
// Smooth transition (300ms)
<div className="transition-smooth">
  All properties transition smoothly
</div>

// Fast transition (150ms)
<div className="transition-fast">
  Quick transitions for subtle effects
</div>
```

**Use Case**: Color changes, size changes, any property transition

---

### Hover Effects

```jsx
// Lift effect on hover
<div className="hover-lift">
  Moves up 4px on hover
</div>

// Combine with transitions
<button className="transition-smooth hover-lift hover:shadow-xl">
  Professional button with lift and shadow
</button>
```

**Use Case**: Cards, buttons, interactive elements

---

## 🎯 Common Patterns

### Professional Button

```jsx
<button className="
  px-6 py-3 
  bg-indigo-600 text-white font-semibold 
  rounded-xl shadow-lg
  hover:bg-indigo-700 hover:shadow-xl
  transition-smooth hover-lift
  active:scale-95
  disabled:opacity-50 disabled:cursor-not-allowed
">
  Click Me
</button>
```

**Features**:
- Smooth color transition
- Shadow increase on hover
- Lift effect on hover
- Scale down on click
- Proper disabled state

---

### Animated Card

```jsx
<div className="
  bg-white rounded-xl border border-gray-200 p-6
  hover:border-indigo-200 hover:shadow-lg
  transition-smooth hover-lift
  animate-slide-up
">
  Card content with entrance animation
</div>
```

**Features**:
- Slides up on mount
- Lifts on hover
- Border color transition
- Shadow increase

---

### Loading Overlay

```jsx
{loading && (
  <div className="
    absolute inset-0 
    bg-white/95 backdrop-blur-sm 
    rounded-2xl 
    flex flex-col items-center justify-center 
    z-10 
    animate-fade-in
  ">
    <div className="w-16 h-16 mb-4">
      <svg className="animate-spin text-indigo-600" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>
    <p className="text-lg font-semibold text-gray-900 mb-2 animate-pulse-subtle">
      {progressMessage}
    </p>
    <div className="w-48 h-1 bg-gray-200 rounded-full overflow-hidden">
      <div className="h-full bg-indigo-600 animate-shimmer"></div>
    </div>
  </div>
)}
```

**Features**:
- Fades in smoothly
- Backdrop blur
- Spinning loader
- Pulsing text
- Shimmer progress bar

---

### Staggered List Animation

```jsx
{items.map((item, index) => (
  <div 
    key={index}
    className="animate-slide-up"
    style={{ animationDelay: `${index * 100}ms` }}
  >
    {item.content}
  </div>
))}
```

**Features**:
- Each item slides up
- Staggered by 100ms per item
- Creates cascading effect

---

### Error Message

```jsx
{error && (
  <div className="
    mt-3 
    text-sm text-red-600 
    flex items-center gap-2 
    animate-slide-down
  ">
    <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    {error}
  </div>
)}
```

**Features**:
- Slides down from top
- Icon for visual clarity
- Red color for errors

---

### Success State

```jsx
{success && (
  <div className="
    mt-4 
    flex items-center gap-2 
    text-teal-600 
    animate-scale-in
  ">
    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
    <span className="font-medium">Success!</span>
  </div>
)}
```

**Features**:
- Scales in for emphasis
- Checkmark icon
- Teal color for success

---

## 🎨 Color Palette Reference

### Primary Colors
```css
Indigo-50:  #EEF2FF (backgrounds)
Indigo-100: #E0E7FF (hover states)
Indigo-500: #6366F1 (accents)
Indigo-600: #4F46E5 (primary buttons)
Indigo-700: #4338CA (hover states)
```

### Success Colors
```css
Teal-50:  #F0FDFA (backgrounds)
Teal-100: #CCFBF1 (hover states)
Teal-500: #14B8A6 (accents)
Teal-600: #0D9488 (success states)
Teal-700: #0F766E (hover states)
```

### Warning/Error Colors
```css
Orange-50:  #FFF7ED (backgrounds)
Orange-600: #EA580C (warnings)
Red-600:    #DC2626 (errors)
```

### Neutral Colors
```css
Gray-50:  #F9FAFB (backgrounds)
Gray-100: #F3F4F6 (borders)
Gray-200: #E5E7EB (dividers)
Gray-500: #6B7280 (secondary text)
Gray-600: #4B5563 (body text)
Gray-900: #111827 (headings)
```

---

## 📏 Spacing Scale

```css
Gap-2:  0.5rem (8px)
Gap-3:  0.75rem (12px)
Gap-4:  1rem (16px)
Gap-6:  1.5rem (24px)
Gap-8:  2rem (32px)
Gap-12: 3rem (48px)

Padding-4: 1rem (16px)
Padding-6: 1.5rem (24px)
Padding-8: 2rem (32px)
Padding-10: 2.5rem (40px)
```

---

## 🔤 Typography Scale

```css
text-xs:   0.75rem (12px)
text-sm:   0.875rem (14px)
text-base: 1rem (16px)
text-lg:   1.125rem (18px)
text-xl:   1.25rem (20px)
text-2xl:  1.5rem (24px)
text-3xl:  1.875rem (30px)
text-4xl:  2.25rem (36px)
text-5xl:  3rem (48px)

font-medium:  500
font-semibold: 600
font-bold:     700
font-black:    900
```

---

## 🎯 Best Practices

### DO ✅
- Use `transition-smooth` for most transitions
- Combine `hover-lift` with shadow increases
- Add `active:scale-95` to buttons for feedback
- Use staggered animations for lists (100ms delay)
- Apply `animate-fade-in` to page-level components
- Use `animate-slide-up` for cards and sections

### DON'T ❌
- Don't stack multiple animations on the same element
- Don't use animations longer than 500ms
- Don't animate on every state change
- Don't use `transform` and animation classes together
- Don't forget disabled states for loading elements

---

## 🚀 Performance Tips

1. **Use CSS Transforms**: Always prefer `transform` over `top/left/width/height`
   ```jsx
   // Good ✅
   <div className="hover:-translate-y-1">
   
   // Bad ❌
   <div className="hover:top-[-4px]">
   ```

2. **GPU Acceleration**: Transforms and opacity are GPU-accelerated
   ```jsx
   // GPU-accelerated ✅
   transform, opacity
   
   // CPU-bound ❌
   width, height, margin, padding
   ```

3. **Debounce State Updates**: For loading states, debounce rapid updates
   ```jsx
   // Good ✅
   setTimeout(() => setProgress("Next step..."), 800)
   
   // Bad ❌
   setProgress("Next step...")
   setProgress("Another step...")
   setProgress("Final step...")
   ```

4. **Use `will-change` Sparingly**: Only for elements that will definitely animate
   ```css
   /* Only if needed */
   .will-animate {
     will-change: transform, opacity;
   }
   ```

---

## 📱 Responsive Considerations

### Mobile Optimizations
```jsx
// Reduce animation on mobile
<div className="
  animate-slide-up 
  lg:animate-slide-up 
  motion-reduce:animate-none
">
  Respects user preferences
</div>

// Adjust hover effects for touch
<button className="
  hover:bg-indigo-700 
  active:bg-indigo-800
  lg:hover-lift
">
  No lift on mobile, only color change
</button>
```

---

## 🎬 Animation Timing Reference

```javascript
// Page transitions
Page Load:     300ms fade-in
Page Exit:     200ms fade-out

// Element animations
Card Entry:    400ms slide-up
List Items:    100ms stagger
Buttons:       200ms all transitions
Modals:        300ms scale-in

// Loading states
Spinner:       Infinite rotation
Shimmer:       2s infinite
Pulse:         2s infinite

// Micro-interactions
Hover:         200ms
Active:        150ms
Focus:         200ms
```

---

## 🔍 Debugging Animations

### Check Animation Performance
```javascript
// In browser DevTools
1. Open Performance tab
2. Start recording
3. Trigger animation
4. Stop recording
5. Look for green bars (good) vs red bars (jank)
```

### Common Issues

**Animation Not Working**:
- Check if class is applied: Inspect element
- Verify CSS is loaded: Check Network tab
- Check for conflicting styles: Computed styles

**Animation Janky**:
- Use GPU-accelerated properties only
- Reduce animation complexity
- Check for layout thrashing

**Animation Too Fast/Slow**:
- Adjust duration in `index.css`
- Use `transition-fast` or `transition-smooth`
- Add custom duration: `duration-[500ms]`

---

## 📚 Additional Resources

### Tailwind CSS
- [Transitions](https://tailwindcss.com/docs/transition-property)
- [Transforms](https://tailwindcss.com/docs/transform)
- [Animations](https://tailwindcss.com/docs/animation)

### Web Animations
- [MDN: CSS Animations](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations)
- [MDN: CSS Transitions](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Transitions)

---

**Last Updated**: January 2, 2026  
**Version**: 1.0  
**Maintained By**: TalkSense AI Team
