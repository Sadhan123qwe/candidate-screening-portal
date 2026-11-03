interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const lastPage = Math.max(1, Math.ceil(total / pageSize));
  const firstRow = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastRow = Math.min(page * pageSize, total);

  return (
    <nav aria-label="Pagination" className="flex items-center justify-between border-t border-gray-200 px-4 py-3 text-sm text-gray-600">
      <span>
        {firstRow}&ndash;{lastRow} of {total}
      </span>
      <div className="flex items-center gap-2">
        <button type="button" className="btn-secondary py-1" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </button>
        <span>
          Page {page} of {lastPage}
        </span>
        <button type="button" className="btn-secondary py-1" disabled={page >= lastPage} onClick={() => onPageChange(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  );
}
