/** Bump this to force every parent back through re-consent (see consent-accept). */
export const CURRENT_CONSENT_VERSION = 'v1'

export const CURRENT_CONSENT_DOCUMENT = {
    version: CURRENT_CONSENT_VERSION,
    sections: [
        {
            title: 'Why we ask',
            body: 'MiniMoney needs your consent to record your child\'s task activity and Mbuck earnings, under South Africa\'s POPIA.',
        },
        {
            title: 'What we store',
            body: 'Your Google account email, your children\'s registered emails, names and ages, task history, and Mbuck ledger entries. Nothing is sold or shared with third parties.',
        },
        {
            title: 'Mbucks are not money',
            body: 'Mbucks cannot be transferred, cashed out, or redeemed for real currency. They exist only to track completed tasks inside this app.',
        },
    ],
}
