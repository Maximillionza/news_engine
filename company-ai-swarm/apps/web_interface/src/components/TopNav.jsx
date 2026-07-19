import React from "react";

// Persistent rounded bar (spec sec.10): mail, COO chat, risks, approvals, settings.
// Inline SVG icons matching the mockups; badges show unread/pending counts.

function Icon({ children }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

export default function TopNav({ open, onOpen, badges }) {
  const items = [
    {
      id: "mail",
      title: "Communications",
      icon: (
        <Icon>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M3 7l9 6 9-6" />
        </Icon>
      ),
    },
    {
      id: "coo",
      title: "COO chat",
      icon: (
        <Icon>
          <path d="M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z" />
        </Icon>
      ),
    },
    {
      id: "risks",
      title: "Risks and issues",
      icon: (
        <Icon>
          <path d="M12 3l10 18H2L12 3z" />
          <path d="M12 10v5" />
          <circle cx="12" cy="18" r="0.4" fill="currentColor" />
        </Icon>
      ),
    },
    {
      id: "approvals",
      title: "Evolution approvals",
      icon: (
        <Icon>
          <rect x="4" y="4" width="16" height="16" rx="3" />
          <path d="M8.5 12.5l2.5 2.5 4.5-5.5" />
        </Icon>
      ),
    },
    {
      id: "settings",
      title: "Settings",
      icon: (
        <Icon>
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5 5l2.1 2.1M16.9 16.9L19 19M19 5l-2.1 2.1M7.1 16.9L5 19" />
        </Icon>
      ),
    },
  ];

  return (
    <nav className="topnav">
      {items.map((item) => (
        <button
          key={item.id}
          title={item.title}
          className={open === item.id ? "active" : ""}
          onClick={() => onOpen(item.id)}
        >
          {item.icon}
          {badges[item.id] > 0 && <span className="badge">{badges[item.id] > 9 ? "9+" : badges[item.id]}</span>}
        </button>
      ))}
    </nav>
  );
}
