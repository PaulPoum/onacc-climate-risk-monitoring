# pages/01_Splash.py
# pages/01_Splash.py
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="ONACC Climate Risk",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Router (à exécuter tôt) ---
go = st.query_params.get("go")
if go == "connexion":
    st.query_params.clear()
    st.switch_page("pages/02_Connexion.py")
elif go == "demande_acces":
    st.query_params.clear()
    st.switch_page("pages/03_Demande_acces.py")

# --- Styles globaux + iframe background + animations avancées ---
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebar"] { display: none; }
        #MainMenu { display: none; }
        footer { display: none; }

        .main .block-container {
            padding: 0;
            max-width: 100%;
        }
        .main { padding: 0; }

        /* Iframe en plein écran (fond) */
        iframe {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw !important;
            height: 100vh !important;
            border: none;
            z-index: 1;
            pointer-events: none;
        }


        /* Overlay Streamlit au-dessus de l'iframe */
        .oc-overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%;
            height: 100%;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            text-align: center;
            pointer-events: none;
        }

        /* Logo animé */
        .oc-logo-container {
            margin-bottom: 2rem;
            animation: fadeInDown 1.2s ease-out;
        }

        .oc-logo {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
            animation: float 3s ease-in-out infinite;
            margin: 0 auto;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes scaleIn {
            from {
                opacity: 0;
                transform: scale(0.9);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        .oc-title {
            font-size: 4rem;
            font-weight: 900;
            margin-bottom: 1.5rem;
            letter-spacing: -2px;
            margin-top: 1rem;
            background: linear-gradient(135deg, #fff 0%, #a8edea 50%, #fed6e3 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: fadeInDown 1s ease-out 0.2s both;
            position: relative;
        }

        .oc-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 4px;
            background: linear-gradient(90deg, transparent, #667eea, transparent);
            border-radius: 2px;
            animation: glow 2s ease-in-out infinite;
        }

        @keyframes glow {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; box-shadow: 0 0 20px rgba(102, 126, 234, 0.8); }
        }

        .oc-subtitle {
            font-size: 1.4rem;
            margin-bottom: 3rem;
            opacity: 0.95;
            font-weight: 400;
            max-width: 700px;
            line-height: 1.8;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
            padding: 0 20px;
            animation: fadeInUp 1s ease-out 0.4s both;
        }

        .oc-subtitle strong {
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #ffd89b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .oc-button-container {
            display: flex;
            gap: 1.5rem;
            margin-top: 2rem;
            flex-wrap: wrap;
            justify-content: center;
            pointer-events: all;
            animation: scaleIn 1s ease-out 0.6s both;
        }

        .custom-button {
            padding: 1.2rem 3rem;
            font-size: 1.1rem;
            font-weight: 700;
            border-radius: 60px;
            border: none;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.7rem;
            position: relative;
            overflow: hidden;
            letter-spacing: 0.5px;
        }

        .custom-button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }

        .custom-button:hover::before {
            width: 300px;
            height: 300px;
        }

        .custom-button span {
            position: relative;
            z-index: 1;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 8px 30px rgba(102, 126, 234, 0.4);
        }

        .btn-primary:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 12px 40px rgba(102, 126, 234, 0.6);
        }

        .btn-primary:active {
            transform: translateY(-1px) scale(0.98);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.15);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.25);
            border-color: rgba(255, 255, 255, 0.9);
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 12px 40px rgba(255, 255, 255, 0.3);
        }

        .btn-secondary:active {
            transform: translateY(-1px) scale(0.98);
        }

        .oc-features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin-top: 4rem;
            max-width: 1000px;
            padding: 0 20px;
            pointer-events: all;
            animation: fadeInUp 1s ease-out 0.8s both;
        }

        .feature {
            background: rgba(255, 255, 255, 0.08);
            padding: 2rem 1.5rem;
            border-radius: 20px;
            backdrop-filter: blur(20px);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            position: relative;
            overflow: hidden;
        }

        .feature::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transform: scaleX(0);
            transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .feature:hover::before {
            transform: scaleX(1);
        }

        .feature:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateY(-8px);
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 0 15px 50px rgba(102, 126, 234, 0.3);
        }

        .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
            transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .feature:hover .feature-icon {
            transform: scale(1.1) rotate(5deg);
        }

        .feature-text {
            font-size: 1rem;
            opacity: 0.95;
            line-height: 1.5;
            font-weight: 500;
        }

        /* Particles background */
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            pointer-events: none;
        }

        .particle {
            position: absolute;
            width: 3px;
            height: 3px;
            background: rgba(255, 255, 255, 0.5);
            border-radius: 50%;
            animation: particleFloat 20s linear infinite;
        }

        @keyframes particleFloat {
            0% {
                transform: translateY(100vh) translateX(0);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(-100vh) translateX(100px);
                opacity: 0;
            }
        }

        /* Scroll indicator */
        .scroll-indicator {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            animation: bounce 2s infinite;
            pointer-events: all;
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.9rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }

        .scroll-indicator::after {
            content: '⌄';
            font-size: 1.5rem;
        }

        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% {
                transform: translateX(-50%) translateY(0);
            }
            40% {
                transform: translateX(-50%) translateY(-10px);
            }
            60% {
                transform: translateX(-50%) translateY(-5px);
            }
        }

        @media (max-width: 768px) {
            .oc-title { 
                font-size: 2.8rem;
                margin-top: 0;
            }
            .oc-subtitle { 
                font-size: 1.1rem;
                line-height: 1.6;
            }
            .feature { 
                padding: 1.5rem 1rem;
            }
            .oc-features {
                grid-template-columns: repeat(2, 1fr);
                gap: 1rem;
            }
            .custom-button {
                padding: 1rem 2rem;
                font-size: 1rem;
            }
        }

        @media (max-width: 480px) {
            .oc-features {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Globe 3D (fond) : version améliorée avec étoiles scintillantes ---
globe_bg_html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    html, body { width:100%; height:100%; overflow:hidden; }
    body { 
        background: radial-gradient(ellipse at bottom, #1b2735 0%, #090a0f 100%);
    }
    #canvas-container { position:fixed; top:0; left:0; width:100%; height:100%; }
    .loading {
      position: fixed; top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      font-size: 1.3rem;
      color: white;
      z-index: 3;
      text-align: center;
      font-family: 'Inter', -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto, Oxygen, Ubuntu, sans-serif;
    }
    .loading-spinner {
      width: 60px; height: 60px;
      border: 5px solid rgba(102, 126, 234, 0.2);
      border-top-color: #667eea;
      border-radius: 50%;
      animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
      margin: 0 auto 1.5rem;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-text {
        font-weight: 500;
        letter-spacing: 1px;
        animation: pulse 1.5s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
  </style>
</head>
<body>
  <div id="loading" class="loading">
    <div class="loading-spinner"></div>
    <div class="loading-text">Chargement de la Terre...</div>
  </div>

  <div id="canvas-container"></div>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script>
    let scene, camera, renderer, earth, clouds, atmosphere;
    let mouseX = 0, mouseY = 0;
    let targetRotationX = 0, targetRotationY = 0;

    function init() {
      scene = new THREE.Scene();
      
      camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
      camera.position.z = 2.8;

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      document.getElementById('canvas-container').appendChild(renderer.domElement);

      // Ambient light
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
      scene.add(ambientLight);

      // Directional light (sun)
      const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
      directionalLight.position.set(5, 3, 5);
      scene.add(directionalLight);

      // Back light
      const backLight = new THREE.PointLight(0x4a90e2, 0.8);
      backLight.position.set(-5, -3, -5);
      scene.add(backLight);

      const loadingManager = new THREE.LoadingManager();
      let loadedTextures = 0;
      const totalTextures = 2;
      
      loadingManager.onProgress = function(url, loaded, total) {
        loadedTextures = loaded;
        const percent = Math.round((loaded / total) * 100);
        document.querySelector('.loading-text').textContent = `Chargement ${percent}%`;
      };
      
      loadingManager.onLoad = function() {
        setTimeout(() => {
          const loading = document.getElementById('loading');
          loading.style.transition = 'opacity 0.5s ease-out';
          loading.style.opacity = '0';
          setTimeout(() => { loading.style.display = 'none'; }, 500);
        }, 800);
      };

      const textureLoader = new THREE.TextureLoader(loadingManager);

      const earthGroup = new THREE.Group();
      earthGroup.rotation.z = -0.1;
      scene.add(earthGroup);

      const geometry = new THREE.SphereGeometry(1, 128, 128);

      const dayTexture = textureLoader.load(
        'https://raw.githubusercontent.com/turban/webgl-earth/master/images/2_no_clouds_4k.jpg'
      );
      const nightTexture = textureLoader.load(
        'https://raw.githubusercontent.com/turban/webgl-earth/master/images/5_night_4k.jpg'
      );

      const earthMaterial = new THREE.MeshPhongMaterial({
        map: dayTexture,
        bumpScale: 0.05,
        specular: new THREE.Color(0x333333),
        shininess: 20,
        emissive: new THREE.Color(0x000000),
        emissiveMap: nightTexture,
        emissiveIntensity: 1.2
      });

      earth = new THREE.Mesh(geometry, earthMaterial);
      earthGroup.add(earth);

      // Clouds with better texture
      const cloudGeometry = new THREE.SphereGeometry(1.008, 128, 128);
      const cloudCanvas = document.createElement('canvas');
      cloudCanvas.width = 4096;
      cloudCanvas.height = 2048;
      const cloudContext = cloudCanvas.getContext('2d');

      cloudContext.fillStyle = 'rgba(0, 0, 0, 0)';
      cloudContext.fillRect(0, 0, cloudCanvas.width, cloudCanvas.height);

      cloudContext.fillStyle = 'rgba(255, 255, 255, 0.7)';
      for (let i = 0; i < 1000; i++) {
        const x = Math.random() * cloudCanvas.width;
        const y = Math.random() * cloudCanvas.height;
        const radius = Math.random() * 60 + 20;
        cloudContext.beginPath();
        cloudContext.arc(x, y, radius, 0, Math.PI * 2);
        cloudContext.fill();
      }

      const cloudTexture = new THREE.CanvasTexture(cloudCanvas);
      const cloudMaterial = new THREE.MeshPhongMaterial({
        map: cloudTexture,
        transparent: true,
        opacity: 0.4,
        depthWrite: false,
        side: THREE.DoubleSide
      });

      clouds = new THREE.Mesh(cloudGeometry, cloudMaterial);
      earthGroup.add(clouds);

      // Atmosphere glow - improved
      const atmosphereGeometry = new THREE.SphereGeometry(1.18, 128, 128);
      const atmosphereMaterial = new THREE.ShaderMaterial({
        uniforms: { 
            c: { type: "f", value: 0.5 }, 
            p: { type: "f", value: 6.0 } 
        },
        vertexShader: `
          varying vec3 vNormal;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform float c;
          uniform float p;
          varying vec3 vNormal;
          void main() {
            float intensity = pow(c - dot(vNormal, vec3(0.0, 0.0, 1.0)), p);
            gl_FragColor = vec4(0.4, 0.7, 1.0, 1.0) * intensity;
          }
        `,
        side: THREE.BackSide,
        blending: THREE.AdditiveBlending,
        transparent: true
      });

      atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
      earthGroup.add(atmosphere);

      // Enhanced stars
      const starsGeometry = new THREE.BufferGeometry();
      const starsMaterial = new THREE.PointsMaterial({ 
        color: 0xffffff, 
        size: 2,
        transparent: true,
        opacity: 1,
        sizeAttenuation: true
      });

      const starsVertices = [];
      const starsColors = [];
      
      for (let i = 0; i < 20000; i++) {
        const x = (Math.random() - 0.5) * 2000;
        const y = (Math.random() - 0.5) * 2000;
        const z = -Math.random() * 2000;
        starsVertices.push(x, y, z);
        
        // Random star colors
        const color = new THREE.Color();
        color.setHSL(Math.random() * 0.2 + 0.5, 0.5, 0.8);
        starsColors.push(color.r, color.g, color.b);
      }

      starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starsVertices, 3));
      starsGeometry.setAttribute('color', new THREE.Float32BufferAttribute(starsColors, 3));
      
      starsMaterial.vertexColors = true;
      
      const stars = new THREE.Points(starsGeometry, starsMaterial);
      scene.add(stars);

      // Mouse interaction
      document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
      }, false);

      // Window resize
      window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      }, false);

      animate();
    }

    function animate() {
      requestAnimationFrame(animate);

      earth.rotation.y += 0.0006;
      if (clouds) clouds.rotation.y += 0.0008;
      if (atmosphere) atmosphere.rotation.y -= 0.0002;

      targetRotationX = mouseX * 0.4;
      targetRotationY = mouseY * 0.4;

      camera.position.x += (targetRotationX - camera.position.x) * 0.03;
      camera.position.y += (targetRotationY - camera.position.y) * 0.03;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    }

    init();
  </script>
</body>
</html>
"""

components.html(globe_bg_html, height=None, scrolling=False)

# --- Overlay HTML amélioré ---
overlay_html = """
<div class="oc-overlay">
  <div class="oc-logo-container">
    <div class="oc-logo">🌍</div>
  </div>
  
  <h1 class="oc-title">ONACC Climate Risk</h1>
  <p class="oc-subtitle">
    Plateforme intelligente de <strong>suivi</strong> et d'<strong>analyse</strong> des risques et catastrophes climatiques au Cameroun
  </p>

  <div class="oc-button-container">
    <a class="custom-button btn-primary" href="?go=connexion">
      <span>🔐</span>
      <span>Connexion</span>
    </a>
    <a class="custom-button btn-secondary" href="?go=demande_acces">
      <span>📝</span>
      <span>Demander l'accès</span>
    </a>
  </div>

  <div class="oc-features">
    <div class="feature">
      <div class="feature-icon">📊</div>
      <div class="feature-text">Tableaux de bord temps réel</div>
    </div>
    <div class="feature">
      <div class="feature-icon">🗺️</div>
      <div class="feature-text">Cartographie interactive</div>
    </div>
    <div class="feature">
      <div class="feature-icon">🌦️</div>
      <div class="feature-text">Données climatiques</div>
    </div>
    <div class="feature">
      <div class="feature-icon">⚠️</div>
      <div class="feature-text">Alertes précoces</div>
    </div>
  </div>
</div>
"""
st.markdown(overlay_html, unsafe_allow_html=True)