const ctx = document.getElementById('graficoHoras');

new Chart(ctx,{
    type:'bar',

    data:{

        labels:['Jan','Fev','Mar','Abr','Mai','Jun'],

        datasets:[{

            label:'Horas',

            data:[4,12,7,3,2,16],

            borderRadius:8

        }]

    },

    options:{

        plugins:{
            legend:{
                display:false
            }
        },

        responsive:true,

        scales:{

            y:{
                beginAtZero:true
            }

        }

    }

});