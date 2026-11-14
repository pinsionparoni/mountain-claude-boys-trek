// Line icons for the S-mobiili mock-up, drawn for this prototype in S-mobiili's
// line style; no S-Bank logos or brand assets. They inherit colour from CSS
// (currentColor), so every icon in the app looks the same.
import type { ReactNode } from "react";

const Svg = ({ children, size = 24 }: { children: ReactNode; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
);

export const ChatIcon = () => <Svg><path d="M4 5h16v11H9l-5 4z" /></Svg>;
export const ChatDotIcon = () => (
  <Svg><path d="M4 5h12M20 9v7H9l-5 4V5" /><circle cx="19.5" cy="4.5" r="1.8" fill="currentColor" stroke="none" /></Svg>
);
export const ChatsIcon = () => <Svg><path d="M3 4h12v9H7l-4 3zM9 16v1h8l4 3V8h-3" /></Svg>;
export const CoachIcon = () => (
  <Svg><path d="M4 5h16v11H9l-5 4z" /><path d="M8 13l3-3 2 2 3-4" /></Svg>
);
export const BackIcon = () => <Svg><path d="M15 5l-7 7 7 7" /></Svg>;
export const ChevronIcon = () => <Svg size={20}><path d="M9 5l7 7-7 7" /></Svg>;
export const PlusIcon = () => <Svg><path d="M12 5v14M5 12h14" /></Svg>;
export const BagIcon = () => <Svg><path d="M5 8h14v12H5z M9 8V6a3 3 0 0 1 6 0v2" /><path d="M12 16.5l-2-2a1.3 1.3 0 0 1 2-1.6 1.3 1.3 0 0 1 2 1.6z" /></Svg>;
export const BookmarkIcon = () => <Svg><path d="M7 4h10v16l-5-4-5 4z" /></Svg>;
export const LogoutIcon = () => <Svg><path d="M14 4H5v16h9M10 12h11M17 8l4 4-4 4" /></Svg>;
export const InfoIcon = () => <Svg><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5v.5" /></Svg>;
export const FeedbackIcon = () => <Svg><path d="M4 5h16v11H9l-5 4z" /><path d="M12 7.5l1 2 2 .3-1.5 1.4.4 2-1.9-1-1.9 1 .4-2L9 9.8l2-.3z" /></Svg>;
export const MailIcon = () => <Svg><rect x="3" y="5" width="18" height="14" rx="1" /><path d="M3 6l9 7 9-7M3 19l7-6M21 19l-7-6" /></Svg>;
export const ExternalIcon = () => <Svg size={20}><path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6" /></Svg>;
export const AccountIcon = () => <Svg><rect x="5" y="3" width="14" height="18" rx="1" /><path d="M9 3v18" /></Svg>;
export const CardIcon = () => <Svg><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M3 10h18" /></Svg>;
export const SendIcon = () => <Svg><path d="M5 12h13M13 6l6 6-6 6" /></Svg>;
export const SparkIcon = () => (
  <Svg><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" /></Svg>
);
export const HomeIcon = () => <Svg><path d="M4 11l8-7 8 7v9h-5v-6h-6v6H4z" /></Svg>;
export const WalletIcon = () => <Svg><path d="M4 7h14a2 2 0 0 1 2 2v9H4z M4 7l11-3v3" /><path d="M16 13h2" /></Svg>;
export const PersonIcon = () => <Svg><circle cx="12" cy="8" r="4" /><path d="M4 21c1-4 4-6 8-6s7 2 8 6" /></Svg>;
export const ReceiptIcon = () => <Svg><path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" /><path d="M9 8h6M9 12h6M9 16h3" /></Svg>;
export const BarcodeIcon = () => (
  <Svg><path d="M4 7V5h3M17 5h3v2M20 17v2h-3M7 19H4v-2M8 9v6M11 9v6M13 9v6M16 9v6" /></Svg>
);
export const QrIcon = () => (
  <Svg><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 18h2v2h-2zM18 14h2M14 18v2" /></Svg>
);
export const ShieldIcon = () => <Svg><path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" /><circle cx="12" cy="10" r="2" /><path d="M12 12v4" /></Svg>;
export const KeyIcon = () => <Svg><circle cx="7" cy="12" r="3" /><path d="M10 12h11M18 12v3M15 12v2" /></Svg>;
export const IdCardIcon = () => <Svg><rect x="3" y="5" width="18" height="14" rx="1" /><circle cx="8.5" cy="11" r="2" /><path d="M5.5 16c.5-1.5 1.6-2 3-2s2.5.5 3 2M14 10h4M14 13h4" /></Svg>;
export const DocIcon = () => <Svg><path d="M6 3h9l4 4v14H6z" /><path d="M9 11h7M9 15h7M9 7h4" /></Svg>;
export const SavingsIcon = () => <Svg><path d="M4 18l5-5 4 3 7-8" /><path d="M15 8h5v5" /></Svg>;
export const LoanIcon = () => <Svg><path d="M4 11l8-6 8 6M6 10v9h12v-9" /><path d="M10 19v-5h4v5" /></Svg>;
export const PayIcon = () => <Svg><path d="M4 12h12M12 8l4 4-4 4M20 5v14" /></Svg>;
