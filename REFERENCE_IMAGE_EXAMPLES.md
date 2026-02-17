# Reference Image Feature - Examples & Guide

## What is the Reference Image Feature?

The reference image feature uses **Image-to-Image (img2img)** generation, where the AI takes your uploaded product photo and transforms it while maintaining the core structure, composition, and key features.

Think of it as: **Your Photo** + **AI Enhancement** = **Professional Marketing Image**

## How It Works

### Technical Details
- **Prompt Strength:** 0.75 (75% transformation)
- This means:
  - 25% stays true to your reference image (structure, composition, layout)
  - 75% is influenced by your description and style (quality, lighting, background)

### The Process
1. You upload a product photo
2. AI analyzes the composition, lighting, and structure
3. AI applies your description and style preset
4. Result: Enhanced, professional version maintaining the original essence

## Example Use Cases

### Example 1: Background Cleanup

**Reference Image:**
- Product: Smartwatch on a messy desk
- Issues: Cluttered background, poor lighting, amateur photo

**Your Inputs:**
- Description: "premium smartwatch with black screen and leather strap, clean white background, professional studio lighting"
- Style: Professional

**Generated Result:**
- Same smartwatch composition
- Clean white background
- Professional studio lighting
- Marketing-ready image

---

### Example 2: Quality Enhancement

**Reference Image:**
- Product: Perfume bottle, basic phone photo
- Issues: Low resolution, dull colors, basic lighting

**Your Inputs:**
- Description: "luxury perfume bottle with golden cap and elegant glass design, premium lighting, sophisticated presentation"
- Style: Luxury

**Generated Result:**
- Same bottle design
- Enhanced colors and details
- Professional lighting
- Luxury aesthetic

---

### Example 3: Style Transformation

**Reference Image:**
- Product: Running shoes, standard product photo
- Issues: Generic, not attention-grabbing

**Your Inputs:**
- Description: "athletic running shoes with dynamic design, vibrant colors, energetic presentation"
- Style: Vibrant

**Generated Result:**
- Same shoe model
- More vibrant, eye-catching colors
- Dynamic presentation
- Social media ready

---

### Example 4: Multiple Campaign Versions

**Single Reference Image:**
- Product: Wireless earbuds in case

**Generate 4 Versions:**

1. **Professional Style**
   - Description: "wireless earbuds in charging case, corporate, clean"
   - Use: E-commerce listing

2. **Luxury Style**
   - Description: "premium wireless earbuds, elegant, sophisticated"
   - Use: Premium brand positioning

3. **Modern Style**
   - Description: "contemporary wireless earbuds, sleek design"
   - Use: Tech blog reviews

4. **Vibrant Style**
   - Description: "colorful wireless earbuds, energetic"
   - Use: Social media ads

---

## When to Use Reference Images

### ✅ Use Reference Images When:

1. **You have a product photo** that needs enhancement
2. **You want consistent composition** across variations
3. **You need to maintain specific product details**
4. **You want to clean up backgrounds** without losing product structure
5. **You're creating variations** for different marketing channels
6. **You want more predictable results**

### ❌ Skip Reference Images When:

1. **You're exploring completely new concepts**
2. **You want maximum creative freedom**
3. **You don't have any product photos yet**
4. **You want the AI to imagine everything from scratch**

---

## Tips for Best Results with Reference Images

### 1. Reference Image Quality

**Good Reference Images:**
- ✅ Clear focus on product
- ✅ Good lighting (doesn't have to be perfect)
- ✅ Product is main subject
- ✅ Adequate resolution (at least 512x512)

**Bad Reference Images:**
- ❌ Very blurry or out of focus
- ❌ Product is tiny in frame
- ❌ Extremely dark or overexposed
- ❌ Multiple products causing confusion

### 2. Description Strategy

**With Reference Image:**
- Focus on what you want to CHANGE/IMPROVE
- Mention desired background and lighting
- Keep product description consistent with reference

**Example:**
- Reference: Basic smartwatch photo
- Description: "premium smartwatch with professional studio lighting, clean white background, high-end presentation"
- The AI knows what the smartwatch looks like (from reference)
- Your description guides the transformation

### 3. Prompt Strength Explained

Current setting: **0.75** (balanced)

**What this means:**
- **Lower (0.5-0.6):** Stays very close to reference, subtle changes
- **Current (0.75):** Good balance - maintains structure but allows transformation
- **Higher (0.85-0.9):** More creative freedom, might diverge more from reference

**Our setting gives you:**
- Product structure maintained ✓
- Composition preserved ✓
- Significant quality enhancement ✓
- Style transformation applied ✓

---

## Real-World Workflow Examples

### Scenario 1: E-Commerce Seller

**Challenge:** Product photos taken with phone, need professional images

**Solution:**
```
1. Upload phone photo of product
2. Description: "[product] with clean white background, professional studio lighting, high quality product photography"
3. Style: Professional
4. Generate → Use for product listing
```

### Scenario 2: Social Media Marketing

**Challenge:** Need eye-catching ads for Instagram

**Solution:**
```
1. Upload product photo
2. Description: "[product] with vibrant presentation, eye-catching, social media ready"
3. Style: Vibrant
4. Generate → Perfect for social ads
```

### Scenario 3: Multi-Channel Campaign

**Challenge:** Need different image styles for different platforms

**Solution:**
```
Upload same reference once, then:

For Amazon/Website:
- Style: Professional
- Generate clean, standard product image

For Premium Retailers:
- Style: Luxury
- Generate high-end presentation

For Instagram:
- Style: Vibrant
- Generate eye-catching version

For LinkedIn/B2B:
- Style: Professional + "corporate aesthetic"
- Generate business-focused version
```

### Scenario 4: Product Line Consistency

**Challenge:** Multiple products need consistent style

**Solution:**
```
For each product:
1. Upload product photo
2. Use identical description format
3. Same style preset
4. Result: Consistent marketing materials across entire line
```

---

## Comparison: With vs Without Reference

### Without Reference (Text-to-Image)
- **Freedom:** Maximum creative freedom
- **Predictability:** Less predictable
- **Use case:** Concept exploration, no existing photos
- **Result:** AI imagines everything from description

### With Reference (Image-to-Image)
- **Freedom:** Structured transformation
- **Predictability:** More predictable
- **Use case:** Enhancing existing photos
- **Result:** AI enhances your actual product

**Pro Tip:** Try both! Generate without reference first to explore, then use your favorite as a reference for refinement.

---

## Advanced Tips

### Tip 1: Iterative Refinement
```
1. Generate with reference
2. Download result
3. Use that result as new reference
4. Apply further refinements
5. Repeat until perfect
```

### Tip 2: Style Mixing
```
Generate with different styles from same reference:
- Compare results
- Pick elements you like from each
- Use best one as new reference
- Describe the elements you want to keep
```

### Tip 3: Description Focus

**For background changes:**
"[product], clean white background, studio lighting"

**For quality boost:**
"[product], professional photography, high quality, sharp focus"

**For aesthetic shift:**
"[product], [style adjectives], [mood descriptors]"

---

## Frequently Asked Questions

**Q: Will it completely replace my product?**
A: No! With prompt_strength at 0.75, your product's structure is maintained. The AI enhances rather than replaces.

**Q: Can I use sketches or drawings?**
A: Yes! The AI will try to create a realistic version based on your sketch.

**Q: What if I want it to stay closer to the reference?**
A: The current 0.75 strength is optimized for enhancement while maintaining structure. Contact developer to adjust if needed.

**Q: Can I remove unwanted objects?**
A: Yes! Don't mention them in your description. Example: reference has a pen next to product → don't mention pen in description → it may disappear.

**Q: How many times can I regenerate?**
A: As many as you want! Each costs ~$0.01. Try multiple variations.

---

## Quick Reference Checklist

Before generating with reference image:

- [ ] Reference image is clear and well-lit
- [ ] Product is main focus of reference
- [ ] Description mentions desired changes
- [ ] Style preset selected
- [ ] Background preference specified
- [ ] Lighting requirements mentioned

Ready to generate! 🚀

---

## Need Help?

- Review [USAGE_GUIDE.md](USAGE_GUIDE.md) for general usage
- Check [README.md](README.md) for setup
- See [QUICKSTART.md](QUICKSTART.md) to get started

Happy enhancing! 📸✨
