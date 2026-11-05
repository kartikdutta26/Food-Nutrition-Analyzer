export const EMPTY_USER_PROFILE = {
  name: '',
  age: '',
  height: '',
  weight: '',
  activityLevel: '',
  goal: '',
  waterTarget: '',
  dietary_preferences: [],
  targets: null,
};

export function getProfileInitial(name, email) {
  const source = typeof name === 'string' && name.trim()
    ? name
    : typeof email === 'string'
      ? email
      : '';
  return [...source.trim()][0]?.toLocaleUpperCase() || '?';
}

export function profileFromApi(profile) {
  return {
    name: profile.name ?? '',
    age: profile.age ?? '',
    height: profile.height_cm ?? '',
    weight: profile.weight_kg ?? '',
    activityLevel: profile.activity_level ?? '',
    goal: profile.goal ?? '',
    waterTarget: profile.water_liters ?? '',
    dietary_preferences: profile.dietary_preferences ?? [],
    targets: profile.targets ?? null,
  };
}

function numberOrNull(value) {
  if (value === '' || value === null || value === undefined) return null;
  return Number(value);
}

export function profileUpdateToApi(profile) {
  const targets = profile.targets || {};
  const hasAnyMacroTarget = ['calories', 'protein', 'carbs', 'fats']
    .some((key) => targets[key] !== '' && targets[key] !== null && targets[key] !== undefined);

  return {
    name: profile.name?.trim() || null,
    age: numberOrNull(profile.age),
    height_cm: numberOrNull(profile.height),
    weight_kg: numberOrNull(profile.weight),
    activity_level: profile.activityLevel || null,
    goal: profile.goal || null,
    water_liters: numberOrNull(profile.waterTarget),
    dietary_preferences: profile.dietary_preferences || [],
    ...(hasAnyMacroTarget ? {
      targets: {
        calories: Number(targets.calories),
        protein: Number(targets.protein),
        carbs: Number(targets.carbs),
        fats: Number(targets.fats),
      },
    } : {}),
  };
}
