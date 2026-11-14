// S-Etukortti tab, laid out like S-mobiili. Coupon products are neutral placeholders:
// the real coupons show other companies' packaging, which our permission doesn't cover.
import type { Text } from "../lib/i18n";
import { BagIcon, BarcodeIcon, BookmarkIcon, ReceiptIcon } from "./Icons";
import { SLogo } from "./SLogo";

const coupons = (h: Text["home"]) => [
  { name: h.couponA, euros: "4", cents: "99", shape: "cheese", redeemable: true },
  { name: h.couponB, euros: "2", cents: "95", shape: "sweets", redeemable: false },
  { name: h.couponC, euros: "5", cents: "49", shape: "coffee", redeemable: false },
];

export function EtukorttiPage({ t }: { t: Text }) {
  const h = t.home;
  return (
    <>
      <div className="sm-ek-top">
        <div className="sm-ek-card">
          <SLogo className="sm-ek-logo" />
          <span className="sm-ek-name">S-ETUKORTTI</span>
          <span className="sm-ek-barcode" title={h.notInDemo}><BarcodeIcon /></span>
        </div>
      </div>

      <div className="sm-section">
        <div className="sm-tiles">
          <span className="sm-tile" title={h.notInDemo}><span className="sm-row-icon"><BagIcon /></span>{h.bonusAndPurchases}</span>
          <span className="sm-tile" title={h.notInDemo}><span className="sm-row-icon"><ReceiptIcon /></span>{h.receipts}</span>
        </div>

        <div className="sm-heading-row">
          <h2 className="sm-heading">{h.yourBenefits}</h2>
          <span className="sm-link">{h.showAll}</span>
        </div>
        <div className="sm-hscroll">
          {coupons(h).map((c) => (
            <article key={c.name} className="sm-coupon">
              <div className={`sm-coupon-image sm-coupon-image--${c.shape}`} aria-hidden="true">
                <span className="sm-coupon-bookmark"><BookmarkIcon /></span>
                {c.redeemable && <span className="sm-coupon-tag">{h.redeemable}</span>}
              </div>
              <p className="sm-coupon-kind">{h.coupon}</p>
              <p className="sm-coupon-name">{c.name}</p>
              <p className="sm-coupon-price">{c.euros}<sup>{c.cents}</sup></p>
              <p className="sm-coupon-valid">{h.validUntil("30.11.")}</p>
              <p className="sm-coupon-store"><span className="sm-store-badge">S</span>{h.storeMore(198)}</p>
            </article>
          ))}
        </div>

        <div className="sm-heading-row">
          <h2 className="sm-heading">{h.campaigns}</h2>
          <span className="sm-link">{h.showAll}</span>
        </div>
        <div className="sm-hscroll">
          <article className="sm-campaign sm-campaign--stripes">
            <span className="sm-campaign-big">−15%</span>
            <span className="sm-campaign-text">{h.campaignA}</span>
          </article>
          <article className="sm-campaign sm-campaign--warm">
            <span className="sm-campaign-text">{h.campaignB}</span>
          </article>
        </div>
      </div>
    </>
  );
}
