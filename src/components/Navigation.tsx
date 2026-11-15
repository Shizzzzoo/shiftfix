import {
  LayoutDashboard,
  MessageSquare,
  ClipboardList,
  Inbox,
  Activity,
  Workflow,
  Zap,
  ClipboardCheck,
  Gauge,
  Package,
  Tags,
  Factory,
  MapPin,
  Users,
  UserRound,
  Download,
  Archive,
  CreditCard,
  HelpCircle,
  ChevronDown,
} from "lucide-react";
export function Navigation({
  page,
  role,
  onSelect,
}: {
  page: string;
  role: string;
  onSelect: (p: string) => void;
}) {
  const manage = ["admin", "manager"].includes(role),
    staff = role !== "reporter";
  const button = (label: string, Icon: any) => (
    <button
      key={label}
      title={label}
      aria-label={label}
      aria-current={page === label ? "page" : undefined}
      className={page === label ? "active" : ""}
      onClick={() => onSelect(label)}
    >
      <Icon size={18} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
  const group = (name: string, Icon: any, pages: string[]) => (
    <details className="nav-group" open key={name}>
      <summary title={name}>
        <Icon size={18} aria-hidden="true" />
        <span>{name}</span>
        <ChevronDown size={13} aria-hidden="true" />
      </summary>
      <div>{pages.map((p) => button(p, Icon))}</div>
    </details>
  );
  return (
    <nav aria-label="Main navigation" className="expanded-nav">
      {button("Overview", LayoutDashboard)}
      {button("Maintiny", MessageSquare)}
      {manage && button("Review inbox", Inbox)}
      {group("Work management", ClipboardList, [
        "Work orders",
        ...(staff ? ["Upcoming"] : []),
        ...(manage ? ["Recurrence"] : []),
      ])}
      {button("Asset monitoring", Activity)}
      {button("Requests", Inbox)}
      {manage && button("Workflows", Workflow)}
      {manage && button("Automations", Zap)}
      {staff &&
        group("Inspections", ClipboardCheck, [
          ...(manage ? ["Inspection templates"] : []),
          "Inspection responses",
        ])}
      {staff && button("Meters", Gauge)}
      {staff &&
        group("Inventory", Package, [
          ...(manage ? ["Vendors"] : []),
          "Parts",
          "Part types",
          "Part locations",
          "Life tracking",
          ...(manage ? ["Purchase management"] : []),
        ])}
      {button("Categories", Tags)}
      {group("Assets", Factory, ["Assets", "Asset types"])}
      {group("Locations", MapPin, ["Locations", "Zones", "Sub-zones"])}
      {manage && button("Teams", Users)}
      {manage && button("Users", UserRound)}
      {button("Download centre", Download)}
      {manage && button("Billing & usage", CreditCard)}
      {manage && button("Bulk archive", Archive)}
      {manage && button("Archive", Archive)}
      {button("My profile", UserRound)}
      {button("Help & accessibility", HelpCircle)}
    </nav>
  );
}
