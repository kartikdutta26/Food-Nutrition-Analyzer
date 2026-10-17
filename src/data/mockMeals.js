// Local-only profile fields kept for the existing profile form. The backend
// persists dietary_preferences and targets separately through /api/profile.
export const INITIAL_USER_PROFILE = {
  name: '',
  age: '',
  height: '',
  weight: '',
  activityLevel: 'Moderate',
  goal: '',
  localWaterTarget: '',
};
