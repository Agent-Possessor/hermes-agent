# Feature Catalog

> Status principle: describe items as “available in the product experience” only when confirmed in the live release. The repository demonstrates product intent and implementation scope, but it is not a substitute for release verification.

## 1. Wallet creation and recovery
**What it does:** Helps users create a new wallet or restore an existing wallet using their own recovery information.

**User value:** Reduces the barrier to entering Web3 while preserving user ownership of wallet access.

**Safe explanation:** “Your recovery phrase is your access backup. Keep it private and offline; anyone who has it may control the wallet.”

## 2. Multi-chain asset view
**What it does:** Brings supported assets and networks into one wallet experience.

**User value:** Less switching between multiple apps; faster review of holdings and activity.

## 3. Send and receive assets
**What it does:** Lets users receive funds through their wallet address or QR code and send supported assets after reviewing destination, amount, network, and fee.

**User value:** Makes basic wallet actions easier to complete and review.

**Critical caution:** Sending to the wrong network or wrong address may lead to permanent loss. Users must check the recipient address and selected network.

## 4. Transaction review and confirmation
**What it does:** Presents the key details of a transaction or signature request before the user approves it.

**User value:** Gives users an opportunity to detect mistakes, unexpected approvals, or suspicious requests.

**Examples of details to review:** destination, amount, estimated cost, token permission, contract interaction, and expected balance impact.

## 5. Security warnings and approval awareness
**What it does:** Surfaces caution signals around actions such as unlimited token approvals, unknown contract interactions, NFT approvals, or simulated failures.

**User value:** Helps users make more informed decisions before assets or permissions are affected.

**Important limitation:** Warnings reduce risk but cannot guarantee that a transaction is safe. Users remain responsible for final approval.

## 6. dApp connection and signing
**What it does:** Allows users to connect their wallet to compatible decentralized applications and review requests to connect, sign messages, approve permissions, or submit transactions.

**User value:** Enables access to Web3 services without leaving the wallet flow.

**Safe explanation:** “Connecting a wallet does not automatically transfer assets, but signing or approving a request can grant permissions. Review each prompt carefully.”

## 7. Browser and phishing awareness
**What it does:** Provides a Web3 browsing experience and may flag suspicious or phishing-related destinations.

**User value:** Helps users navigate dApps with stronger awareness of destination risk.

**Important limitation:** A warning system may not detect every malicious site. Users should verify URLs independently.

## 8. Address book / bookmarks
**What it does:** Lets users save frequently used wallet addresses or destinations with recognizable labels.

**User value:** Reduces repetitive entry and helps avoid sending to the wrong saved destination.

## 9. Activity and transaction history
**What it does:** Gives users a record of wallet activity and transaction outcomes.

**User value:** Easier tracking, troubleshooting, and financial awareness.

## 10. NFT visibility and transfers
**What it does:** Supports viewing supported NFT assets and, where available, transferring them.

**User value:** Lets collectors manage digital collectibles alongside token balances.

## 11. Cross-chain bridge experience
**What it does:** Helps users compare or initiate a route to move supported assets from one blockchain ecosystem to another.

**User value:** Reduces the complexity of multi-step cross-network movement.

**Critical caution:** Bridge transfers may involve route constraints, fees, waiting time, slippage, third-party protocol risk, and destination-network risk. No route should be described as guaranteed best or risk-free.

## 12. QR scan for wallet and payment requests
**What it does:** Lets users scan supported QR codes for wallet connection or payment-related details.

**User value:** Faster input and lower risk of manually mistyping addresses.

## 13. Market and AI assistance direction
**What it does:** The repository includes an emerging Dompet-Ku Agent direction for conversational help such as gas-fee questions, transaction simulation prompts, and bridge recommendations.

**How to describe it:** “Dompet-Ku is developing assistant capabilities to help users understand wallet actions and options.”

**Do not say:** “The AI will trade for you,” “The AI guarantees the best route,” or “The AI replaces your final review.”

## 14. Settings and personalization
**What it does:** Includes language and appearance preferences, as well as product settings such as saved destinations and security-related views.

**User value:** Makes the wallet easier to use across different user preferences.
