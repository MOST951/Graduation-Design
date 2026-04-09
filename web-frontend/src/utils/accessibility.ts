// Accessibility utilities for Vue 3 applications

// ARIA roles and properties
export const ARIA_ROLES = {
  BUTTON: 'button',
  LINK: 'link',
  NAVIGATION: 'navigation',
  MAIN: 'main',
  COMPLEMENTARY: 'complementary',
  CONTENTINFO: 'contentinfo',
  BANNER: 'banner',
  SEARCH: 'search',
  FORM: 'form',
  DIALOG: 'dialog',
  ALERT: 'alert',
  STATUS: 'status',
  TABLIST: 'tablist',
  TAB: 'tab',
  TABPANEL: 'tabpanel',
  MENU: 'menu',
  MENUITEM: 'menuitem',
  LISTBOX: 'listbox',
  OPTION: 'option',
  GRID: 'grid',
  GRIDCELL: 'gridcell',
  ROW: 'row',
  ROWHEADER: 'rowheader',
  COLUMNHEADER: 'columnheader'
} as const

// Accessibility states
export const ARIA_STATES = {
  BUSY: 'aria-busy',
  CHECKED: 'aria-checked',
  DISABLED: 'aria-disabled',
  EXPANDED: 'aria-expanded',
  HIDDEN: 'aria-hidden',
  INVALID: 'aria-invalid',
  PRESSED: 'aria-pressed',
  SELECTED: 'aria-selected',
  REQUIRED: 'aria-required'
} as const

// Accessibility properties
export const ARIA_PROPERTIES = {
  LABEL: 'aria-label',
  LABELLEDBY: 'aria-labelledby',
  DESCRIBEDBY: 'aria-describedby',
  LIVE: 'aria-live',
  ATOMIC: 'aria-atomic',
  RELEVANT: 'aria-relevant',
  DROPEFFECT: 'aria-dropeffect',
  GRABBED: 'aria-grabbed',
  ACTIVEDESCENDANT: 'aria-activedescendant',
  CONTROLS: 'aria-controls',
  AUTOCOMPLETE: 'aria-autocomplete',
  HASPOPUP: 'aria-haspopup',
  LEVEL: 'aria-level',
  POSINSET: 'aria-posinset',
  SETSIZE: 'aria-setsize',
  SORT: 'aria-sort',
  VALUEMAX: 'aria-valuemax',
  VALUEMIN: 'aria-valuemin',
  VALUENOW: 'aria-valuenow',
  VALUETEXT: 'aria-valuetext'
} as const

// Live region priorities
export const LIVE_REGIONS = {
  OFF: 'off',
  POLITE: 'polite',
  ASSERTIVE: 'assertive'
} as const

// Accessibility helper functions
export class AccessibilityHelper {
  // Generate unique IDs for accessibility
  static generateId(prefix: string = 'a11y'): string {
    return `${prefix}-${Math.random().toString(36).substr(2, 9)}`
  }

  // Create accessible button attributes
  static getButtonAttributes(label?: string, disabled = false, pressed = false) {
    const attrs: Record<string, string | boolean> = {
      role: ARIA_ROLES.BUTTON,
      tabindex: disabled ? -1 : 0
    }

    if (label) attrs[ARIA_PROPERTIES.LABEL] = label
    if (disabled) attrs[ARIA_STATES.DISABLED] = true
    if (pressed !== undefined) attrs[ARIA_STATES.PRESSED] = pressed

    return attrs
  }

  // Create accessible link attributes
  static getLinkAttributes(label?: string, disabled = false) {
    const attrs: Record<string, string | boolean> = {
      role: ARIA_ROLES.LINK,
      tabindex: disabled ? -1 : 0
    }

    if (label) attrs[ARIA_PROPERTIES.LABEL] = label
    if (disabled) attrs[ARIA_STATES.DISABLED] = true

    return attrs
  }

  // Create accessible input attributes
  static getInputAttributes(
    label?: string,
    required = false,
    invalid = false,
    describedBy?: string
  ) {
    const attrs: Record<string, string | boolean> = {}

    if (label) attrs[ARIA_PROPERTIES.LABEL] = label
    if (required) attrs[ARIA_STATES.REQUIRED] = true
    if (invalid) attrs[ARIA_STATES.INVALID] = true
    if (describedBy) attrs[ARIA_PROPERTIES.DESCRIBEDBY] = describedBy

    return attrs
  }

  // Create accessible table cell attributes
  static getTableCellAttributes(
    isHeader = false,
    scope?: 'row' | 'col',
    sort?: 'none' | 'ascending' | 'descending'
  ) {
    const attrs: Record<string, string> = {
      role: isHeader ? ARIA_ROLES.COLUMNHEADER : ARIA_ROLES.GRIDCELL
    }

    if (isHeader && scope) attrs.scope = scope
    if (sort) attrs[ARIA_PROPERTIES.SORT] = sort

    return attrs
  }

  // Create accessible dialog attributes
  static getDialogAttributes(label?: string, describedBy?: string, modal = true) {
    const attrs: Record<string, string> = {
      role: ARIA_ROLES.DIALOG,
      [ARIA_PROPERTIES.LABEL]: label || '',
      'aria-modal': modal.toString()
    }

    if (describedBy) attrs[ARIA_PROPERTIES.DESCRIBEDBY] = describedBy

    return attrs
  }

  // Create accessible tab attributes
  static getTabAttributes(selected = false, controls?: string) {
    const attrs: Record<string, string | boolean> = {
      role: ARIA_ROLES.TAB,
      tabindex: selected ? 0 : -1,
      [ARIA_STATES.SELECTED]: selected
    }

    if (controls) attrs[ARIA_PROPERTIES.CONTROLS] = controls

    return attrs
  }

  // Create accessible tab panel attributes
  static getTabPanelAttributes(labelledBy?: string, hidden = false) {
    const attrs: Record<string, string | boolean> = {
      role: ARIA_ROLES.TABPANEL,
      [ARIA_STATES.HIDDEN]: hidden,
      tabindex: 0
    }

    if (labelledBy) attrs[ARIA_PROPERTIES.LABELLEDBY] = labelledBy

    return attrs
  }

  // Create accessible live region attributes
  static getLiveRegionAttributes(
    priority: keyof typeof LIVE_REGIONS = 'polite',
    atomic = false
  ) {
    return {
      [ARIA_PROPERTIES.LIVE]: LIVE_REGIONS[priority],
      [ARIA_PROPERTIES.ATOMIC]: atomic.toString()
    }
  }

  // Create accessible progress bar attributes
  static getProgressAttributes(
    value: number,
    min = 0,
    max = 100,
    label?: string
  ) {
    const attrs: Record<string, string | number> = {
      role: 'progressbar',
      [ARIA_PROPERTIES.VALUENOW]: value,
      [ARIA_PROPERTIES.VALUEMIN]: min,
      [ARIA_PROPERTIES.VALUEMAX]: max
    }

    if (label) attrs[ARIA_PROPERTIES.LABEL] = label

    return attrs
  }

  // Create accessible slider attributes
  static getSliderAttributes(
    value: number,
    min = 0,
    max = 100,
    label?: string,
    describedBy?: string
  ) {
    const attrs: Record<string, string | number> = {
      role: 'slider',
      [ARIA_PROPERTIES.VALUENOW]: value,
      [ARIA_PROPERTIES.VALUEMIN]: min,
      [ARIA_PROPERTIES.VALUEMAX]: max,
      tabindex: 0
    }

    if (label) attrs[ARIA_PROPERTIES.LABEL] = label
    if (describedBy) attrs[ARIA_PROPERTIES.DESCRIBEDBY] = describedBy

    return attrs
  }

  // Create accessible menu attributes
  static getMenuAttributes(label?: string) {
    const attrs: Record<string, string> = {
      role: ARIA_ROLES.MENU
    }

    if (label) attrs[ARIA_PROPERTIES.LABEL] = label

    return attrs
  }

  // Create accessible menu item attributes
  static getMenuItemAttributes(disabled = false, checked = false) {
    const attrs: Record<string, string | boolean> = {
      role: ARIA_ROLES.MENUITEM,
      tabindex: -1
    }

    if (disabled) attrs[ARIA_STATES.DISABLED] = true
    if (checked !== undefined) attrs[ARIA_STATES.CHECKED] = checked

    return attrs
  }

  // Announce message to screen readers
  static announce(message: string, priority: keyof typeof LIVE_REGIONS = 'polite') {
    // Create or find live region
    let liveRegion = document.getElementById('a11y-live-region')
    
    if (!liveRegion) {
      liveRegion = document.createElement('div')
      liveRegion.id = 'a11y-live-region'
      liveRegion.setAttribute('aria-live', LIVE_REGIONS[priority])
      liveRegion.setAttribute('aria-atomic', 'true')
      liveRegion.className = 'sr-only'
      document.body.appendChild(liveRegion)
    }

    // Update message
    liveRegion.textContent = message
    
    // Clear after announcement
    setTimeout(() => {
      liveRegion.textContent = ''
    }, 1000)
  }

  // Focus management
  static focusElement(selector: string | HTMLElement) {
    const element = typeof selector === 'string' 
      ? document.querySelector(selector) as HTMLElement
      : selector

    if (element) {
      element.focus()
    }
  }

  // Trap focus within a container
  static trapFocus(container: HTMLElement) {
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>

    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus()
            e.preventDefault()
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus()
            e.preventDefault()
          }
        }
      }
    }

    container.addEventListener('keydown', handleTabKey)

    // Return cleanup function
    return () => {
      container.removeEventListener('keydown', handleTabKey)
    }
  }

  // Check if element is visible
  static isElementVisible(element: HTMLElement): boolean {
    return !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length)
  }

  // Get visible focusable elements
  static getVisibleFocusableElements(container?: HTMLElement): HTMLElement[] {
    const selector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    const elements = container 
      ? container.querySelectorAll(selector)
      : document.querySelectorAll(selector)

    return Array.from(elements).filter(el => 
      this.isElementVisible(el as HTMLElement) && 
      !(el as HTMLElement).disabled
    ) as HTMLElement[]
  }

  // Set up keyboard navigation
  static setupKeyboardNavigation(
    container: HTMLElement,
    options: {
      orientation?: 'horizontal' | 'vertical'
      loop?: boolean
      onEnter?: (element: HTMLElement) => void
      onSpace?: (element: HTMLElement) => void
      onEscape?: () => void
    } = {}
  ) {
    const {
      orientation = 'horizontal',
      loop = true,
      onEnter,
      onSpace,
      onEscape
    } = options

    const focusableElements = this.getVisibleFocusableElements(container)
    let currentIndex = 0

    const handleKeyDown = (e: KeyboardEvent) => {
      const isHorizontal = orientation === 'horizontal'
      const nextKey = isHorizontal ? 'ArrowRight' : 'ArrowDown'
      const prevKey = isHorizontal ? 'ArrowLeft' : 'ArrowUp'

      switch (e.key) {
        case nextKey:
          e.preventDefault()
          currentIndex = loop 
            ? (currentIndex + 1) % focusableElements.length
            : Math.min(currentIndex + 1, focusableElements.length - 1)
          focusableElements[currentIndex]?.focus()
          break

        case prevKey:
          e.preventDefault()
          currentIndex = loop 
            ? (currentIndex - 1 + focusableElements.length) % focusableElements.length
            : Math.max(currentIndex - 1, 0)
          focusableElements[currentIndex]?.focus()
          break

        case 'Home':
          e.preventDefault()
          currentIndex = 0
          focusableElements[0]?.focus()
          break

        case 'End':
          e.preventDefault()
          currentIndex = focusableElements.length - 1
          focusableElements[currentIndex]?.focus()
          break

        case 'Enter':
          if (onEnter) {
            e.preventDefault()
            onEnter(e.target as HTMLElement)
          }
          break

        case ' ':
          if (onSpace) {
            e.preventDefault()
            onSpace(e.target as HTMLElement)
          }
          break

        case 'Escape':
          if (onEscape) {
            e.preventDefault()
            onEscape()
          }
          break
      }
    }

    container.addEventListener('keydown', handleKeyDown)

    // Return cleanup function
    return () => {
      container.removeEventListener('keydown', handleKeyDown)
    }
  }
}

// Screen reader only CSS class
export const SR_ONLY = 'sr-only'

// CSS for screen reader only content
export const srOnlyStyles = `
  .sr-only {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    padding: 0 !important;
    margin: -1px !important;
    overflow: hidden !important;
    clip: rect(0, 0, 0, 0) !important;
    white-space: nowrap !important;
    border: 0 !important;
  }

  .sr-only:focus {
    position: static !important;
    width: auto !important;
    height: auto !important;
    padding: inherit !important;
    margin: inherit !important;
    overflow: visible !important;
    clip: auto !important;
    white-space: inherit !important;
  }

  /* Focus indicators */
  *:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  /* Skip to main content link */
  .skip-link {
    position: absolute;
    top: -40px;
    left: 6px;
    background: var(--color-primary);
    color: white;
    padding: 8px;
    text-decoration: none;
    border-radius: var(--border-radius-small);
    z-index: var(--z-index-message);
    transition: top 0.3s;
  }

  .skip-link:focus {
    top: 6px;
  }

  /* High contrast mode support */
  @media (prefers-contrast: high) {
    * {
      border-color: ButtonText !important;
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    * {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
`
