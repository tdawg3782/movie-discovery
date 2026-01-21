<template>
  <div id="app">
    <header>
      <h1>Movie Discovery</h1>
      <nav>
        <router-link to="/">Discover</router-link>
        <router-link to="/watchlist">Watchlist</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
// App shell with Vue Router
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0f0f0f;
  color: #e0e0e0;
}

#app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

header h1 {
  color: #e50914;
}

nav a {
  color: #e0e0e0;
  text-decoration: none;
  margin-left: 20px;
  transition: color 0.2s;
}

nav a:hover {
  color: #e50914;
}

nav a.router-link-active {
  color: #e50914;
}
</style>
