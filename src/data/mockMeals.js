// Pre-loaded realistic meals with Indian & global nutrition data
export const PRESET_MEALS = [
  {
    id: 'paneer-rice',
    name: 'Paneer Rice Bowl',
    category: 'Indian Vegetarian',
    image: 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80',
    calories: 620,
    protein: 28,
    carbs: 72,
    fats: 22,
    fiber: 6,
    score: 8.2,
    insight: 'High in protein but slightly high in carbohydrates. Pair with a fresh cucumber mint salad to balance the glycemic load.',
    ingredients: ['Cottage Cheese (Paneer) - 120g', 'Basmati Steamed Rice - 180g', 'Aromatic Indian Spices', 'Olive & Ghee Glaze - 10ml', 'Green Bell Peppers - 40g'],
    micros: {
      calcium: '380 mg (38% DV)',
      iron: '3.6 mg (20% DV)',
      potassium: '460 mg (13% DV)',
      sodium: '490 mg',
      glycemicIndex: 'Medium (58)'
    }
  },
  {
    id: 'masala-dosa',
    name: 'Crispy Masala Dosa with Sambar',
    category: 'South Indian',
    image: 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=800&q=80',
    calories: 450,
    protein: 12,
    carbs: 68,
    fats: 14,
    fiber: 5.5,
    score: 7.9,
    insight: 'Fermented batter promotes gut microbiome health. Moderately carb-dense; consider enjoying with extra lentil sambar for a protein boost.',
    ingredients: ['Fermented Rice & Urad Dal Batter', 'Spiced Potato Masala', 'Toor Dal Vegetable Sambar', 'Coconut Mint Chutney'],
    micros: {
      calcium: '120 mg (12% DV)',
      iron: '2.8 mg (15% DV)',
      potassium: '520 mg (15% DV)',
      sodium: '580 mg',
      glycemicIndex: 'Medium (62)'
    }
  },
  {
    id: 'dal-tadka',
    name: 'Yellow Dal Tadka & Brown Rice',
    category: 'Home Cooked Classic',
    image: 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80',
    calories: 410,
    protein: 18,
    carbs: 64,
    fats: 8,
    fiber: 11,
    score: 9.2,
    insight: 'Exceptional prebiotic fiber content and clean complex carbohydrates. Very gentle on digestion with sustained energy release.',
    ingredients: ['Yellow Moong & Toor Lentils', 'Steamed Brown Basmati Rice', 'Cumin, Garlic & Tomato Tempering', 'Fresh Coriander'],
    micros: {
      calcium: '140 mg (14% DV)',
      iron: '4.8 mg (27% DV)',
      potassium: '620 mg (18% DV)',
      sodium: '410 mg',
      glycemicIndex: 'Low (42)'
    }
  },
  {
    id: 'chicken-tikka-bowl',
    name: 'Grilled Chicken Tikka Quinoa Bowl',
    category: 'High Protein / Fitness',
    image: 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80',
    calories: 540,
    protein: 48,
    carbs: 42,
    fats: 15,
    fiber: 7.5,
    score: 9.5,
    insight: 'Optimal macro ratio for muscle recovery and metabolic rate. Rich in complete amino acids and bioavailable iron.',
    ingredients: ['Tandoori Spiced Chicken Breast - 160g', 'Organic Fluffy Quinoa - 130g', 'Roast Zucchini & Cherry Tomatoes', 'Tahini Lemon Drizzle'],
    micros: {
      calcium: '95 mg (10% DV)',
      iron: '5.2 mg (29% DV)',
      potassium: '710 mg (21% DV)',
      sodium: '520 mg',
      glycemicIndex: 'Low (36)'
    }
  },
  {
    id: 'palak-paneer',
    name: 'Palak Paneer with Multigrain Roti',
    category: 'Nutrient Dense Green',
    image: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80',
    calories: 480,
    protein: 24,
    carbs: 45,
    fats: 20,
    fiber: 8,
    score: 8.9,
    insight: 'Packed with dietary iron, folate, and calcium from slow-simmered spinach puree and artisan cottage cheese.',
    ingredients: ['Pureed Baby Spinach Gravy', 'Fresh Cottage Cheese Cubes', '2x Multigrain Wholewheat Rotis', 'Ginger & Garam Masala'],
    micros: {
      calcium: '420 mg (42% DV)',
      iron: '6.1 mg (34% DV)',
      potassium: '580 mg (17% DV)',
      sodium: '460 mg',
      glycemicIndex: 'Low (39)'
    }
  },
  {
    id: 'fruit-acai-bowl',
    name: 'Tropical Fruit & Greek Yogurt Platter',
    category: 'Antioxidant Breakfast',
    image: 'https://images.unsplash.com/photo-1511690656952-34342bb7c2f2?auto=format&fit=crop&w=800&q=80',
    calories: 340,
    protein: 16,
    carbs: 54,
    fats: 7,
    fiber: 9,
    score: 9.3,
    insight: 'High in bioactive polyphenols, anthocyanins, and natural vitamin C. Perfect pre-workout fuel.',
    ingredients: ['Dragonfruit & Kiwi Slices', 'Fresh Blueberries & Orange Slices', 'Non-fat Greek Yogurt', 'Chia Seeds & Honey drizzle'],
    micros: {
      calcium: '260 mg (26% DV)',
      iron: '1.8 mg (10% DV)',
      potassium: '490 mg (14% DV)',
      sodium: '75 mg',
      glycemicIndex: 'Low-Medium (48)'
    }
  }
];

export const INITIAL_USER_PROFILE = {
  name: 'Prachi',
  age: 24,
  height: 168, // cm
  weight: 60, // kg
  activityLevel: 'Moderate', // Sedentary, Light, Moderate, Active
  goal: 'Maintain Weight', // 'Gain Muscle', 'Maintain Weight', 'Lose Weight'
  targets: {
    calories: 2000,
    protein: 100,
    carbs: 220,
    fats: 65,
    water: 2.5
  }
};

export const INITIAL_TODAY_LOG = {
  consumedCalories: 1420,
  consumedProtein: 78,
  consumedCarbs: 165,
  consumedFats: 45,
  consumedWater: 1.8,
  meals: [
    {
      id: 'log-1',
      slot: 'Breakfast',
      time: '08:30 AM',
      icon: '🌅',
      name: 'Oatmeal with Berries & Chia Seeds',
      calories: 320,
      protein: 14,
      carbs: 52,
      fats: 6,
      image: 'https://images.unsplash.com/photo-1517673132405-a56a62b18caf?auto=format&fit=crop&w=300&q=80'
    },
    {
      id: 'log-2',
      slot: 'Lunch',
      time: '01:15 PM',
      icon: '☀️',
      name: 'Paneer Rice Bowl',
      calories: 620,
      protein: 28,
      carbs: 72,
      fats: 22,
      image: 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=300&q=80'
    },
    {
      id: 'log-3',
      slot: 'Snack',
      time: '04:45 PM',
      icon: '☕',
      name: 'Green Tea & Roasted Makhana',
      calories: 120,
      protein: 4,
      carbs: 22,
      fats: 2,
      image: 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=300&q=80'
    }
  ]
};
