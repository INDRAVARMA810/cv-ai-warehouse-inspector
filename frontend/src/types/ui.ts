/** Shared UI-level types that are not part of the API contract. */

import type { AlertLevel, SortOrder } from './api';

/** A generic option for select controls. */
export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

/** Column definition for the reusable DataTable. */
export interface Column<T> {
  /** Stable key; also used as the sort key sent to the API. */
  key: string;
  header: string;
  /** Renders the cell. Keeps formatting out of the table itself. */
  render: (row: T) => React.ReactNode;
  /** Whether the API supports sorting by this column's key. */
  sortable?: boolean;
  /** Extra classes applied to both header and body cells. */
  className?: string;
  /** Hide below the `md` breakpoint to keep mobile tables readable. */
  hideOnMobile?: boolean;
}

export interface SortState {
  sortBy?: string;
  order: SortOrder;
}

/** One slice of a severity distribution, used by the charts. */
export interface SeverityDatum {
  level: AlertLevel;
  label: string;
  value: number;
  color: string;
}
