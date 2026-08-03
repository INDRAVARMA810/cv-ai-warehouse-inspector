import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { SelectOption } from '@/types';

const CONTROL_BASE =
  'h-9 w-full rounded-lg border border-surface-600 bg-surface-800 px-3 text-sm text-content-primary ' +
  'placeholder:text-content-muted transition-colors ' +
  'focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/25 ' +
  'disabled:cursor-not-allowed disabled:opacity-50';

/** Plain text input. */
export function Input({ className, ...rest }: ComponentPropsWithoutRef<'input'>) {
  return <input {...rest} className={cn(CONTROL_BASE, className)} />;
}

interface SearchInputProps extends Omit<ComponentPropsWithoutRef<'input'>, 'onChange' | 'value'> {
  value: string;
  onValueChange: (value: string) => void;
}

/**
 * Search box with a leading icon and a clear affordance.
 *
 * Emits raw values on every keystroke; debouncing is the caller's
 * concern (see `useTableQuery`) so this stays purely presentational.
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
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-content-muted"
        aria-hidden
      />
      <input
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onValueChange(event.target.value)}
        {...rest}
        className={cn(CONTROL_BASE, 'pl-9 pr-9 [&::-webkit-search-cancel-button]:hidden')}
      />
      {value ? (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => onValueChange('')}
          className="absolute right-2.5 top-1/2 grid h-5 w-5 -translate-y-1/2 place-items-center rounded text-content-muted transition-colors hover:text-content-primary"
        >
          <X className="h-3.5 w-3.5" />
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
  /** Label for the "no filter" entry. */
  placeholder?: string;
}

/**
 * Filter dropdown.
 *
 * Emits `undefined` for the placeholder entry rather than an empty
 * string, so callers can pass the value straight into a query object
 * without the API receiving `?status=`.
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
      className={cn(CONTROL_BASE, 'cursor-pointer appearance-none pr-8', className)}
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2364748B' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 0.5rem center',
        backgroundSize: '1rem',
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

interface FieldProps {
  label: string;
  children: ReactNode;
  className?: string;
}

/** Labelled wrapper used to lay out filter controls. */
export function Field({ label, children, className }: FieldProps) {
  return (
    <label className={cn('flex min-w-0 flex-col gap-1.5', className)}>
      <span className="text-[11px] font-medium uppercase tracking-wider text-content-muted">
        {label}
      </span>
      {children}
    </label>
  );
}
