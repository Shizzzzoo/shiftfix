import {
  BarChart3,
  ClipboardList,
  Factory,
  MapPin,
  Package,
  CalendarClock,
  ClipboardCheck,
  Users,
  Wrench,
  ShieldCheck,
} from "lucide-react";
export const onboardingRoles: Record<
  string,
  { title: string; description: string; Icon: any }
> = {
  admin: {
    title: "Admin",
    description:
      "Manage access, oversee maintenance and verify repairs across the factory.",
    Icon: ShieldCheck,
  },
  manager: {
    title: "Manager",
    description:
      "Review requests, assign workers, resolve duplicates and verify completed repairs.",
    Icon: Users,
  },
  worker: {
    title: "Worker",
    description:
      "Accept your work, record repairs and return assignments that need a different specialist.",
    Icon: Wrench,
  },
  reporter: {
    title: "Reporter",
    description:
      "Report faults with photos, answer follow-up questions and track your own requests.",
    Icon: ClipboardList,
  },
};
const sections = {
  core: [
    {
      Icon: BarChart3,
      title: "Dashboard & filters",
      text: "See workload, overdue repairs and recent activity. Search directly, or open Filters to narrow by status, dates, asset, owner or factory location.",
    },
    {
      Icon: ClipboardList,
      title: "Work orders & requests",
      text: "A report enters review, gets assigned, is repaired and is verified. Requests and the Review inbox help managers handle duplicates, returned work and completed repairs.",
    },
    {
      Icon: Factory,
      title: "Assets, types & categories",
      text: "Find each machine, its identity and responsible team. Types and categories organize equipment; Asset monitoring brings its open faults and meter readings together.",
    },
    {
      Icon: MapPin,
      title: "Locations, zones & sub-zones",
      text: "Follow the factory hierarchy from a building or area to its zone and specific cell. These connections also power dashboard location filters.",
    },
  ],
  operations: [
    {
      Icon: Package,
      title: "Parts & purchasing",
      text: "Parts, Part types and Part locations organize spares. Vendors and Purchase management track suppliers and receipts. Stock history records issues and replenishment; Life tracking estimates service dates.",
    },
    {
      Icon: CalendarClock,
      title: "Plans, workflows & automations",
      text: "Recurrence and Upcoming organize preventive work. Workflows set acknowledgment, repair and verification deadlines. Automations can turn out-of-range meter readings into review requests.",
    },
    {
      Icon: ClipboardCheck,
      title: "Inspections & meters",
      text: "Inspection templates become repeatable checklists with pass, fail and N/A responses. Meters preserve manual readings and thresholds. No live sensors are connected in this demo.",
    },
    {
      Icon: Users,
      title: "People, downloads & archive",
      text: "Maintiny searches permitted records and prepares drafts for review. My profile keeps your details and access summary. Users control access roles; Teams organize responsibility. Download centre exports CSV and imports asset lists. Finished work can be archived and restored. Billing & usage shows workspace counts.",
    },
  ],
};
export function TourSections({
  section,
  role,
  demoCount,
}: {
  section: "core" | "operations";
  role: string;
  demoCount?: number;
}) {
  return (
    <>
      <p className="tour-role-note">
        {role === "reporter"
          ? "Your Reporter workspace focuses on reporting and tracking your requests. The guide also explains the tools your maintenance team uses."
          : role === "worker"
            ? "Your Worker workspace includes assigned repairs, inspections, readings and available inventory views. Managers handle access and planning."
            : "Your workspace includes the management tools below. Changes remain checked against your access role."}
      </p>
      <div className="tour-grid">
        {sections[section].map(({ Icon, title, text }) => (
          <article className="tour-card" key={title}>
            <Icon size={22} aria-hidden="true" />
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </div>
      {demoCount !== undefined && section === "core" && (
        <div className="tour-demo-note">
          <strong>A populated factory to explore</strong>
          <p>
            {demoCount} fictional work orders and connected assets, stores,
            inspections and locations are already available to management
            accounts. Demo records are labeled; demo people have no login
            access, and demo plans and rules start paused.
          </p>
        </div>
      )}
    </>
  );
}
export function RoleIntro({ role }: { role: string }) {
  const current = onboardingRoles[role] || onboardingRoles.reporter;
  return (
    <>
      <div className="role-intro">
        <current.Icon size={28} aria-hidden="true" />
        <strong>{current.title}</strong>
        <p>{current.description}</p>
      </div>
      <div className="hierarchy">
        {Object.entries(onboardingRoles).map(([key, r]) => (
          <div className={key === role ? "your-role" : ""} key={key}>
            <r.Icon size={20} aria-hidden="true" />
            <div>
              <strong>
                {r.title}
                {key === role ? " · You" : ""}
              </strong>
              <small>{r.description}</small>
            </div>
          </div>
        ))}
      </div>
      <p className="helper">
        Need different access? Ask an Admin or Manager. Your role is never
        self-selected during signup.
      </p>
    </>
  );
}
