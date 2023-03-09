
mkdir -p cache
wget "https://unpkg.com/alpinejs@3.12.0/dist/cdn.min.js" -O cache/alpine-3.12.0.min.js
wget "https://use.fontawesome.com/releases/v6.3.0/fontawesome-free-6.3.0-web.zip" -O cache/fontawesome-free-6.3.0-web.zip
unzip -d cache cache/fontawesome-free-6.3.0-web.zip
rm cache/fontawesome-free-6.3.0-web.zip
wget "https://ajax.googleapis.com/ajax/libs/jquery/3.6.3/jquery.min.js" -O cache/jquery-3.6.3.min.js
wget "https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css" -O cache/bootstrap-4.3.1.min.css
wget "https://cdn.jsdelivr.net/npm/popper.js@1.14.7/dist/umd/popper.min.js" -O cache/popper-1.14.7.min.js
wget "https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/js/bootstrap.min.js" -O cache/bootstrap-4.3.1.min.js
wget "https://cdn.jsdelivr.net/npm/echarts@5.4.1/dist/echarts.min.js" -O cache/echarts-5.4.1.min.js
wget "https://cdn.datatables.net/1.10.19/css/jquery.dataTables.min.css" -O cache/jquery.dataTables-1.10.19.min.css
wget "https://cdn.datatables.net/responsive/2.2.3/css/responsive.dataTables.min.css" -O cache/responsive.dataTables-2.2.3.min.css
wget "https://cdn.datatables.net/responsive/2.2.3/js/dataTables.responsive.min.js" -O cache/dataTables.responsive-2.2.3.min.js