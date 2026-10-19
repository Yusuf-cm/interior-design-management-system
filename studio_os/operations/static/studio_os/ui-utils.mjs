export function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
export function human(value) { return String(value ?? "").toLowerCase().replaceAll("_", " ").replace(/^./, c => c.toUpperCase()); }
export function formatDate(value, detailed = true) {
  if (!value) return "No date set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat("en-KE", {timeZone:"Africa/Nairobi", month:"short", day:"numeric",
    ...(detailed ? {hour:"2-digit", minute:"2-digit"} : {})}).format(date);
}
export function money(value, currency = "KES") {
  // Preserve stored decimal strings; never recompute or coerce totals through Number.
  const match = String(value ?? "0.00").match(/^(-?)(\d+)(\.\d+)?$/);
  if (!match) return currency + " —";
  return currency + " " + match[1] + match[2].replace(/\B(?=(\d{3})+(?!\d))/g,",") + (match[3] || ".00");
}
export function errorText(data) {
  if (typeof data === "string") return data;
  if (Array.isArray(data)) return data.map(errorText).join("\n");
  if (data && typeof data === "object") return Object.entries(data).map(([key,value]) =>
    (key === "detail" || key === "non_field_errors" ? "" : human(key) + ": ") + errorText(value)).join("\n");
  return "This request could not be completed. Try again.";
}
export function nairobiInput(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  // Kenya uses UTC+03:00; these forms explicitly label the scheduling timezone.
  return new Date(date.getTime() + 3*60*60*1000).toISOString().slice(0,16);
}
export function fromNairobiInput(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error("Enter a date and time");
  const iso = value + ":00+03:00";
  if (Number.isNaN(new Date(iso).getTime())) throw new Error("Enter a valid date and time");
  return iso;
}
export function leadTargets(current) {
  return ({NEW:["CONTACTED","DORMANT","LOST"],CONTACTED:["QUALIFIED","DORMANT","LOST"],
    QUALIFIED:["DORMANT","LOST"],CONSULTATION_BOOKED:["LOST"],ASSESSED:["LOST"],
    QUOTED:["DORMANT","LOST"],DORMANT:["CONTACTED","LOST"]})[current] || [];
}
export function routeForAction(action, isField = false) {
  if (action.consultation) return {type:"visit", id:action.consultation};
  if (action.origin_key) {
    const [kind,id] = action.origin_key.split(":");
    return {type:kind === "quote" ? "quote" : kind === "assessment" ? "assessment" : "visit", id:Number(id)};
  }
  return {type:"action", id:action.id};
}
