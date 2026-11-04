/** The three blurred colour blobs that every glass surface picks its colour up from. */
export function Backdrop() {
  return (
    <div aria-hidden="true">
      <div className="blob blob-blue" />
      <div className="blob blob-teal" />
      <div className="blob blob-violet" />
    </div>
  );
}
