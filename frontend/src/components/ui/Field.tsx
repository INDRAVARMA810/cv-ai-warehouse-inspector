import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { SelectOption } from '@/types';

const CONTROL =
  'h-8 w-full rounded-control border border-edge bg-panel-inset px-2.5 text-xs text-ink ' +
  'placeholder:text-ink-ghost transition-colors duration-150 ' +
  'hover:border-edge-strong focus:border-info/60 focus:outline-none focus:ring-1 focus:ring-info/40 ' +
  'disabled:cursor-not-allowed disabled:opacity-40';

/** Plain text input. */
export function Input({ className, ...rest }: ComponentPropsWithoutRef<'input'>) {
  return <input {...rest} className={cn(CONTROL, className)} />;
}

interface SearchInputProps
  extends Omit<ComponentPropsWithoutRef<'input'>, 'onChange' | 'value'> {
  value: string;
  onValueChange: (value: string) => void;
}

/**
 * Search box with a leading glyph and a clear affordance.
 *
 * Emits on every keystroke; debouncing belongs to the caller
 * (`useTableQuery`) so this stays purely presentational.
 */
export function SearchInput({
  value,
  onValueChange,
  className,
  placeholder = 'Search…',
  ...rest
}: SearchInputProps) {
  return (
    <div className={cn('relative', className)}>
      <Search
        className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-ghost"
        aria-hidden
      />
      <input
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onValueChange(event.target.value)}
        {...rest}
        className={cn(CONTROL, 'pl-8 pr-8 [&::-webkit-search-cancel-button]:hidden')}
      />
      {value ? (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => onValueChange('')}
          className="absolute right-2 top-1/2 grid h-4 w-4 -translate-y-1/2 place-items-center rounded-control text-ink-ghost transition-colors hover:text-ink"
        >
          <X className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  );
}

interface SelectProps<T extends string>
  extends Omit<ComponentPropsWithoutRef<'select'>, 'onChange' | 'value'> {
  value: T | '';
  options: readonly SelectOption<T>[];
  onValueChange: (value: T | undefined) => void;
  placeholder?: string;
}

/**
 * Filter dropdown.
 *
 * Emits `undefined` for the placeholder entry rather than an empty
 * string, so the value can be passed straight into a query object
 * without the API receiving a blank parameter it would reject.
 */
export function Select<T extends string>({
  value,
  options,
  onValueChange,
  placeholder = 'All',
  className,
  ...rest
}: SelectProps<T>) {
  return (
    <select
      value={value}
      onChange={(event) => onValueChange((event.target.value || undefined) as T | undefined)}
      {...rest}
      className={cn(CONTROL, 'cursor-pointer appearance-none pr-7', className)}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%235E6873' stroke-width='2.5' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 0.4rem center',
        backgroundSize: '0.85rem',
      }}
    >
      <option value="">{placeholder}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

/** Labelled wrapper for filter controls. */
export function Field({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cn('flex min-w-0 flex-col gap-1', className)}>
      <span className="eyebrow">{label}</span>
      {children}
    </label>
  );
}

/**
 * Segmented toggle for mutually exclusive views.
 *
 * Preferred over a dropdown when there are few options and the current
 * one should stay visible — an operator should not have to open a menu
 * to see which mode a panel is in.
 */
export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: T;
  options: readonly SelectOption<T>[];
  onChange: (value: T) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex items-center gap-0.5 rounded-control border border-edge bg-panel-inset p-0.5',
        className,
      )}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'rounded-control px-2 py-0.5 text-2xs font-medium uppercase tracking-wider transition-colors duration-150',
              active
                ? 'bg-edge-strong text-ink'
                : 'text-ink-ghost hover:text-ink-dim',
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
