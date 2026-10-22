// ORCID-only accounts log in as "<orcid>@orcid.org", which is not a mailbox.
export const publishableEmail = (email) => {
  const value = String(email || '').trim();
  return value.toLowerCase().endsWith('@orcid.org') ? '' : value;
};
