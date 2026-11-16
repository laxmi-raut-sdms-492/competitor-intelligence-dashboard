// Company size labels come from the backend scraper (company_size.category).
const SIZE_ORDER = ['Enterprise', 'Medium Business', 'Small Business', 'Startup', 'Unknown'];

export const getCompanySize = (company) => company?.company_size?.category || 'Unknown';

// e.g. "Enterprise" or "Enterprise · Startup"
export const getSizeLabels = (cleanedData) => {
  if (!cleanedData?.length) return '';
  const sizes = new Set(cleanedData.map(getCompanySize));
  return SIZE_ORDER.filter((size) => sizes.has(size)).join(' · ');
};
