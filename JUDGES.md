# Try the demo

**Mountain Claude Boys · Junction 2026 · S-Pankki: Personal Economic Trainer**

An AI money coach inside an S-mobiili-style app: chat with your own banking data, in Finnish or English. All customers are from S-Pankki's synthetic dataset; no real person's data is involved.

## Open it

| | |
|---|---|
| **Address** | **https://arvon-johannes--financial-coach.modal.run** |
| **Demo passcode** | **`spankkidemo`** |

1. Open the address on your phone (best) or a computer.
2. Choose a language (Suomi / English) and a **demo customer**, type the passcode and tap **Log in**.
3. The home screen opens. Tap **Talousvalmentaja** / **Financial coach** to chat, or the **Talousneuvoja** / **Money adviser** tip's button to ask about it.

The first answer after a quiet spell can take up to half a minute while the server wakes up; after that, answers take a few seconds.

### Install it like an app (optional)

- **Android (Chrome):** ⋮ menu → *Install app* / *Add to Home screen*.
- **iPhone (Safari):** Share → *Add to Home Screen*.

It then opens full-screen from the home screen, like S-mobiili.

## Demo customers

The app's "today" is **10 September 2026**, mid-month, so budgets are in progress.

| Customer | Situation | Good to try |
|---|---|---|
| **CUST00226** · 21 y | Cash tight before payday | "Paljonko voin käyttää tällä viikolla?" |
| **CUST00050** · 23 y | On track | "Millainen kuluttaja olen?" |
| **CUST00127** · 24 y | Budget nearly used | "Mihin rahani menivät viime kuussa?" |
| **CUST00001** · 63 y | Restaurants only in a few months | "Kulutanko enemmän viikonloppuisin vai arkisin?" |

## Questions to ask

Finnish and English both work; ask in either.

**From S-Pankki's brief**
- *Paljonko käytin takseihin viime kuussa?* / How much did I spend on taxis last month?
- *Millainen kuluttaja olen?* / What kind of spender am I? (compared with people your age and with Statistics Finland)
- *Paljonko voin turvallisesti käyttää tällä viikolla?* / What is safe for me to spend this week?
- *Paljonko säästäisin, jos vähentäisin ulkona syömistä 20 %?* / How much could I save if I reduced dining out by 20%?

**Explore your own data** (the coach calculates these on the spot in an isolated sandbox)
- *Kulutanko enemmän viikonloppuisin vai arkisin?* / Do I spend more at weekends or on weekdays?
- *Mihin kellonaikaan teen eniten ostoksia?* / What time of day do I shop the most?
- *Paljonko säästäisin vuodessa, jos jättäisin perjantain ravintolakäynnit pois?*

**Money words and care**
- *Mitä tarkoittaa hätävara?* / What is an emergency fund?
- *Pitäisikö minun ottaa autolaina?* (general explanation, never a personal recommendation)

## What to look for

- **The three baskets** 🏠 🔧 ☕: every purchase is placed in S-Bank's baskets: on the home screen cards, on the receipts and in the answers.
- **Charts on request:** when an answer has a fitting chart, a **📊 Näytä kaaviona** button appears under it; ask "näytä kaaviona" and the chart opens straight away. The AI only chooses the chart; every number comes from code.
- **Talousneuvoja** on the home screen: one tip picked by fixed rules from the customer's own data, with a button that asks the coach the follow-up.
- **Numbers are computed, not guessed:** the AI never does arithmetic itself; it explains figures computed from the customer's transactions.
- **Data stays in Europe:** database in Frankfurt, our server and the calculation sandbox in Modal's EU region, and the AI model (Google's open Gemma 4) on Verda in Finland. One hop isn't in the EU, and we say so: [Where the data goes](README.md#where-the-data-goes).

## If something goes wrong

- **"That passcode didn't work":** check it's `spankkidemo`, all lowercase.
- **No answer for a long time:** wait half a minute (the server is waking up), then tap **Yritä uudelleen** / **Try again**.
- **An old version on the phone:** close the app or tab and open it again.

More about the product: [README.md](README.md) · How it's built: [TECH_STACK.md](TECH_STACK.md)
