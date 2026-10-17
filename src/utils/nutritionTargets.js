const TARGET_KEYS = ['calories', 'protein', 'carbs', 'fats'];
const TARGET_LIMITS = { calories: 100_000, protein: 10_000, carbs: 10_000, fats: 10_000 };

export function validateNutritionTargets(targets) {
  for (const key of TARGET_KEYS) {
    const rawValue = targets?.[key];
    const value = Number(rawValue);

    if (rawValue === '' || rawValue === null || rawValue === undefined || !Number.isFinite(value) || value <= 0) {
      return `${key} must be a number greater than 0.`;
    }
    if (value > TARGET_LIMITS[key]) {
      return `${key} must not exceed ${TARGET_LIMITS[key]}.`;
    }
  }

  return '';
}

export function getTargetProgress(target, total, profileLoaded) {
  const value = target === null || target === undefined || target === ''
    ? Number.NaN
    : Number(target);

  if (!Number.isFinite(value) || value <= 0) {
    return {
      configured: false,
      target: null,
      percent: null,
      label: profileLoaded ? 'Configure target in Profile' : 'Target not loaded',
    };
  }

  const amount = Number.isFinite(Number(total)) ? Number(total) : 0;
  const percent = Math.min(Math.round((amount / value) * 100), 100);
  return { configured: true, target: value, percent, label: `${percent}%` };
}

export function hasNutritionTargets(targets) {
  return TARGET_KEYS.every((key) => getTargetProgress(targets?.[key], 0, true).configured);
}
