'use strict';
module.exports = (req, res) => {
  const providers = [process.env.GROQ_API_KEY && 'groq', process.env.GEMINI_API_KEY && 'gemini'].filter(Boolean);
  res.setHeader('Cache-Control', 'no-store');
  res.status(200).json({ ok: true, version: '2.2.0', llm: providers.length > 0, providers });
};
