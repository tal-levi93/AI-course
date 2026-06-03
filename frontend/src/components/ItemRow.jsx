export default function ItemRow({ item, onToggle, onDelete }) {
  return (
    <div className={`item${item.is_checked ? ' checked' : ''}`}>
      <label className="check">
        <input
          type="checkbox"
          checked={item.is_checked}
          aria-label={`toggle ${item.name}`}
          onChange={(e) => onToggle(item.id, e.target.checked)}
        />
        <span className="box" aria-hidden="true" />
      </label>
      <div className="label">
        {item.name}
        {item.note ? <span className="note">{item.note}</span> : null}
      </div>
      {item.quantity ? <span className="qty">{item.quantity}</span> : null}
      <button
        className="btn-icon"
        type="button"
        aria-label={`delete ${item.name}`}
        onClick={() => onDelete(item.id)}
      >
        Remove
      </button>
    </div>
  )
}
