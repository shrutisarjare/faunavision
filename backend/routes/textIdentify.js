const express = require("express");
const router = express.Router();

// Animal knowledge base
const animals = {
  cat: ["meow", "mew", "kitten", "feline"],
  dog: ["bark", "woof", "puppy"],
  cow: ["moo", "cattle"],
  pig: ["oink"],
  sheep: ["baa"],
  frog: ["croak"]
};

router.post("/identify-text", (req, res) => {
  const { text } = req.body;

  if (!text) {
    return res.json({ prediction: "No text provided" });
  }

  const tokens = text.toLowerCase().split(/\W+/);

  let bestAnimal = null;
  let bestScore = 0;

  for (const animal in animals) {
    let score = 0;
    for (const keyword of animals[animal]) {
      for (const token of tokens) {
        if (token.includes(keyword) || keyword.includes(token)) {
          score++;
        }
      }
    }

    if (score > bestScore) {
      bestScore = score;
      bestAnimal = animal;
    }
  }

  if (bestAnimal) {
    return res.json({ prediction: bestAnimal });
  }

  return res.json({ prediction: "Not an animal description" });
});

module.exports = router;